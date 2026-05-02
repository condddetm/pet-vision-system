"""
用户错误反馈接口

收集用户对识别错误的标注（正确品种），写入 JSONL 日志文件，
供后续微调或错误归因分析使用。
"""
import json
from datetime import datetime
from pathlib import Path
from typing import List, Optional

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from app.core.config import ARTIFACTS_DIR
from app.core.rate_limit import limiter, FEEDBACK_RATE

router = APIRouter(prefix="/api/feedback", tags=["feedback"])

_FEEDBACK_DIR = ARTIFACTS_DIR / "feedback"
_FEEDBACK_DIR.mkdir(parents=True, exist_ok=True)
_FEEDBACK_LOG = _FEEDBACK_DIR / "feedback.jsonl"


class FeedbackPayload(BaseModel):
    file_name: Optional[str] = None
    predicted_breed: str = Field(..., description="模型给出的品种")
    predicted_confidence: float = Field(..., ge=0.0, le=1.0)
    correct_breed: str = Field(..., description="用户标记的真实品种")
    note: Optional[str] = Field(None, max_length=500, description="可选的备注")


@router.post("")
@limiter.limit(FEEDBACK_RATE)
def submit_feedback(request: Request, payload: FeedbackPayload):
    record = {
        "timestamp": datetime.utcnow().isoformat() + "Z",
        **payload.dict(),
    }
    try:
        with _FEEDBACK_LOG.open("a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")
    except OSError as exc:
        raise HTTPException(status_code=500, detail=f"日志写入失败: {exc}")

    return {"ok": True, "saved_at": record["timestamp"]}


@router.get("/recent")
def list_recent(limit: int = 20) -> List[dict]:
    """读取最近 N 条反馈记录"""
    if not _FEEDBACK_LOG.exists():
        return []
    lines: List[str] = []
    with _FEEDBACK_LOG.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                lines.append(line)
    items = []
    for line in lines[-max(0, limit):]:
        try:
            items.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return list(reversed(items))


@router.get("/stats")
def feedback_stats():
    """汇总错误反馈统计"""
    items = list_recent(limit=10_000)
    total = len(items)
    by_predicted: dict[str, int] = {}
    by_correct: dict[str, int] = {}
    confusion_pairs: dict[str, int] = {}
    for it in items:
        pred = it.get("predicted_breed", "?")
        truth = it.get("correct_breed", "?")
        by_predicted[pred] = by_predicted.get(pred, 0) + 1
        by_correct[truth] = by_correct.get(truth, 0) + 1
        key = f"{truth} → {pred}"
        confusion_pairs[key] = confusion_pairs.get(key, 0) + 1
    top_confusions = sorted(confusion_pairs.items(), key=lambda x: -x[1])[:10]
    return {
        "total": total,
        "by_predicted": by_predicted,
        "by_correct": by_correct,
        "top_confusions": [{"pair": k, "count": v} for k, v in top_confusions],
    }
