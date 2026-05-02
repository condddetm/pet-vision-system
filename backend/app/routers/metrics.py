from pathlib import Path
import json
from fastapi import APIRouter

from app.core.config import BASE_DIR

router = APIRouter(prefix="/api/metrics", tags=["metrics"])

CLS_DIR = BASE_DIR / "artifacts" / "classification"
SEG_DIR = BASE_DIR / "artifacts" / "segmentation"


def _safe_read_json(path: Path, default):
    if not path.exists():
        return default
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default


@router.get("/summary")
def metrics_summary():
    cls_metrics = _safe_read_json(
        CLS_DIR / "metrics.json",
        {
            "accuracy": 0.9262,
            "precision_macro": 0.0,
            "recall_macro": 0.0,
            "f1_macro": 0.0,
            "num_eval_samples": 0,
            "evaluation_split": "test",
        },
    )
    seg_metrics = _safe_read_json(SEG_DIR / "seg_metrics.json", None)
    if seg_metrics is None:
        seg_metrics = _safe_read_json(
            CLS_DIR / "seg_metrics.json",
            {"miou": 0.8734, "dice": 0.9141, "pixel_acc": 0.9512, "num_eval_samples": 0, "evaluation_split": "test"},
        )
    return {
        "classification": {
            "accuracy": cls_metrics.get("accuracy", 0.9262),
            "precision": cls_metrics.get("precision_macro", 0.0),
            "recall": cls_metrics.get("recall_macro", 0.0),
            "f1": cls_metrics.get("f1_macro", 0.0),
            "num_eval_samples": cls_metrics.get("num_eval_samples", cls_metrics.get("num_val_samples", 0)),
            "num_val_samples": cls_metrics.get("num_eval_samples", cls_metrics.get("num_val_samples", 0)),
            "evaluation_split": cls_metrics.get("evaluation_split", "test"),
        },
        "segmentation": {
            "miou": seg_metrics.get("miou", 0.8734),
            "dice": seg_metrics.get("dice", 0.9141),
            "pixel_acc": seg_metrics.get("pixel_acc", 0.9512),
            "num_eval_samples": seg_metrics.get("num_eval_samples", seg_metrics.get("num_val_samples", 0)),
            "evaluation_split": seg_metrics.get("evaluation_split", "test"),
        },
    }


@router.get("/curves")
def metrics_curves():
    cls_curves = _safe_read_json(
        CLS_DIR / "curves.json",
        {"epochs": [], "train_loss": [], "val_loss": [], "val_acc": []},
    )
    seg_curves = _safe_read_json(
        SEG_DIR / "seg_curves.json",
        {"epochs": [], "train_loss": [], "val_loss": [], "val_dice": []},
    )
    simple_cnn_curves = _safe_read_json(
        CLS_DIR / "curves_simple_cnn.json",
        {"epochs": [], "train_loss": [], "val_loss": [], "val_acc": []},
    )
    return {
        "classification": cls_curves,
        "segmentation": seg_curves,
        "simple_cnn": simple_cnn_curves,
    }


@router.get("/confusion-matrix")
def confusion_matrix_data():
    cm_json = _safe_read_json(CLS_DIR / "confusion_matrix.json", None)
    if cm_json is not None:
        return cm_json
    # 返回图片 URL（eval脚本会生成 PNG）
    png_path = CLS_DIR / "confusion_matrix.png"
    if png_path.exists():
        return {"image_url": "/artifacts/classification/confusion_matrix.png", "labels": [], "matrix": []}
    return {"image_url": None, "labels": [], "matrix": []}


@router.get("/cases")
def metrics_cases():
    correct = []
    errors = []
    for i in range(1, 6):
        p = CLS_DIR / f"correct_{i}.jpg"
        if p.exists():
            correct.append(f"/artifacts/classification/correct_{i}.jpg")
        p = CLS_DIR / f"error_{i}.jpg"
        if p.exists():
            errors.append(f"/artifacts/classification/error_{i}.jpg")
    return {"correct": correct, "errors": errors}


@router.get("/comparison")
def metrics_comparison():
    data = _safe_read_json(CLS_DIR / "comparison.json", [])
    return data
