"""
WebSocket 推理进度推送

前端建立 WebSocket 连接，发送图片二进制数据后，
后端逐阶段推送结构化日志（JSON），最后推送完整结果与 close。
"""
from __future__ import annotations

import asyncio
import io
import json
import time
from typing import Any, Dict

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from PIL import Image

from app.services.multitask_service import multitask_service

router = APIRouter()


def _now_iso() -> str:
    return time.strftime("%H:%M:%S", time.localtime())


async def _send(ws: WebSocket, level: str, msg: str, **extra) -> None:
    payload: Dict[str, Any] = {"t": _now_iso(), "level": level, "msg": msg}
    payload.update(extra)
    await ws.send_text(json.dumps(payload, ensure_ascii=False))


@router.websocket("/ws/infer")
async def ws_infer(ws: WebSocket):
    await ws.accept()
    try:
        await _send(ws, "info", "WebSocket 已连接，等待图片数据 …")

        # 客户端发送图片字节
        try:
            data = await ws.receive_bytes()
        except WebSocketDisconnect:
            return

        await _send(ws, "info", f"收到图片 {len(data) / 1024:.1f} KB", stage="upload")
        await asyncio.sleep(0.05)

        # 解码
        try:
            image = Image.open(io.BytesIO(data)).convert("RGB")
        except Exception as exc:
            await _send(ws, "error", f"图片解码失败: {exc}")
            await ws.close()
            return

        await _send(ws, "info", f"解码成功 · {image.size[0]}×{image.size[1]} px", stage="decode")
        await asyncio.sleep(0.05)

        await _send(ws, "info", "→ ResNet-34 分类前向 …", stage="cls_start", progress=20)
        t0 = time.perf_counter()
        from app.services.classify_service import classify_service
        from app.services.segment_service import segment_service
        from app.utils.visualize import save_mask_and_overlay
        import numpy as np

        cls_label, cls_conf, top5, cls_latency = classify_service.predict(image)
        await _send(
            ws, "ok",
            f"分类完成 · {cls_label} ({cls_conf * 100:.1f}%) · {cls_latency:.0f} ms",
            stage="cls_done", progress=55,
            partial={"top1": cls_label, "confidence": cls_conf, "top5": top5},
        )

        await _send(ws, "info", "→ U-Net 分割前向 …", stage="seg_start", progress=65)
        seg_t0 = time.perf_counter()
        mask = segment_service.predict_mask(image)
        seg_latency = (time.perf_counter() - seg_t0) * 1000
        await _send(
            ws, "ok",
            f"分割完成 · {seg_latency:.0f} ms",
            stage="seg_done", progress=88,
        )

        # 可视化输出
        await _send(ws, "info", "生成 mask / overlay …", stage="viz", progress=94)
        rgb = np.array(image.convert("RGB"))
        mask_url, overlay_url, area_ratio = save_mask_and_overlay(rgb, mask)

        total_ms = round((time.perf_counter() - t0) * 1000, 2)
        result = {
            "class_top1": cls_label,
            "class_confidence": cls_conf,
            "top5": top5,
            "pet_area_ratio": area_ratio,
            "mask_url": mask_url,
            "overlay_url": overlay_url,
            "latency_ms": total_ms,
        }
        await _send(
            ws, "done",
            f"全部完成 · 总耗时 {total_ms:.0f} ms",
            stage="done", progress=100,
            result=result,
        )
        await ws.close()
    except WebSocketDisconnect:
        return
    except Exception as exc:  # pragma: no cover
        try:
            await _send(ws, "error", f"未预期错误: {exc}")
            await ws.close()
        except Exception:
            pass
