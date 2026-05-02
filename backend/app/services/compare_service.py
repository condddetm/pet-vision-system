"""
三模型对比推理服务

模型对比：
  1. ResNet-34 (ImageNet 预训练 + Fine-tune)  ← 主模型，已训练
  2. ResNet-34 (随机初始化 / 完全未训练)        ← 通过固定 seed 重建，演示无训练效果
  3. SimpleCNN (4 层卷积，从零训练)             ← 已训练

对随机初始化模型，使用固定 random seed=42 确保每次预测一致，
直接体现"未训练的模型 ≈ 1/37 的均匀分布"现象，对比迁移学习价值。
"""
from __future__ import annotations

import sys
import time
from pathlib import Path
from typing import List

import torch
import torch.nn as nn
import torchvision.transforms as T
from torchvision.models import resnet34
from PIL import Image

from app.core.config import WEIGHTS_DIR


# 引入训练目录中的 SimpleCNN 定义
_TRAINING_DIR = Path(__file__).resolve().parents[3] / "training"
if str(_TRAINING_DIR) not in sys.path:
    sys.path.insert(0, str(_TRAINING_DIR))

try:
    from models.simple_cnn import SimpleCNN  # type: ignore
except Exception:  # pragma: no cover
    SimpleCNN = None  # 极端情况下未找到


_BASELINE_ACC = {
    "pretrained": 0.9865,
    "random_init": 0.0270,   # 1/37 期望随机准确率
    "simple_cnn": 0.5115,
}


class CompareService:
    """加载三模型，复用主模型的类别列表与图片预处理"""

    def __init__(self) -> None:
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.img_size = 224
        self.classes: List[str] = []

        self.pretrained = None
        self.random_init = None
        self.simple_cnn = None

        self._load_pretrained()
        self._load_random_init()
        self._load_simple_cnn()

    # ─── Loaders ────────────────────────────────────────────
    def _load_pretrained(self) -> None:
        path = WEIGHTS_DIR / "cls_torch.pth"
        if not path.exists():
            return
        ckpt = torch.load(path, map_location=self.device, weights_only=False)
        self.classes = ckpt.get("classes", [])
        self.img_size = int(ckpt.get("img_size", 224))
        model = resnet34(weights=None)
        model.fc = nn.Linear(model.fc.in_features, len(self.classes))
        model.load_state_dict(ckpt["model_state_dict"])
        self.pretrained = model.to(self.device).eval()

    def _load_random_init(self) -> None:
        if not self.classes:
            return
        # 固定 seed 保证每次"未训练的随机权重"可复现
        torch.manual_seed(42)
        torch.cuda.manual_seed_all(42)
        model = resnet34(weights=None)
        model.fc = nn.Linear(model.fc.in_features, len(self.classes))
        self.random_init = model.to(self.device).eval()

    def _load_simple_cnn(self) -> None:
        if SimpleCNN is None or not self.classes:
            return
        path = WEIGHTS_DIR / "cls_simple_cnn.pth"
        if not path.exists():
            return
        ckpt = torch.load(path, map_location=self.device, weights_only=False)
        model = SimpleCNN(num_classes=len(self.classes))
        state = ckpt.get("model_state_dict", ckpt) if isinstance(ckpt, dict) else ckpt
        model.load_state_dict(state)
        self.simple_cnn = model.to(self.device).eval()

    # ─── Inference ──────────────────────────────────────────
    def _transform(self) -> T.Compose:
        return T.Compose([
            T.Resize((self.img_size, self.img_size)),
            T.ToTensor(),
            T.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
        ])

    def _predict(self, model, image: Image.Image) -> dict:
        if model is None:
            return {"available": False}

        tf = self._transform()
        t0 = time.perf_counter()
        x = tf(image).unsqueeze(0).to(self.device)
        with torch.no_grad():
            logits = model(x)
            probs = torch.softmax(logits, dim=1)[0].detach().cpu().numpy().tolist()
        latency_ms = round((time.perf_counter() - t0) * 1000, 2)

        pairs = sorted(zip(self.classes, probs), key=lambda z: z[1], reverse=True)
        top1_label, top1_conf = pairs[0]
        top5 = [{"label": str(l), "confidence": round(float(c), 4)} for l, c in pairs[:5]]
        return {
            "available": True,
            "top1": str(top1_label),
            "confidence": round(float(top1_conf), 4),
            "top5": top5,
            "latency_ms": latency_ms,
        }

    def infer_all(self, image: Image.Image) -> dict:
        """返回三模型对同一张图的预测对比"""
        if not self.classes:
            return {"error": "Model classes not loaded"}

        models_meta = [
            {
                "key": "pretrained",
                "name": "ResNet-34 (ImageNet 预训练)",
                "short": "ResNet-34 Pretrained",
                "init": "ImageNet 预训练 + Fine-tune",
                "test_acc": _BASELINE_ACC["pretrained"],
                "params": "21.3M",
                "color": "#2563EB",
                "result": self._predict(self.pretrained, image),
            },
            {
                "key": "random_init",
                "name": "ResNet-34 (随机初始化, 未训练)",
                "short": "ResNet-34 Random",
                "init": "随机初始化（无训练）",
                "test_acc": _BASELINE_ACC["random_init"],
                "params": "21.3M",
                "color": "#94A3B8",
                "result": self._predict(self.random_init, image),
            },
            {
                "key": "simple_cnn",
                "name": "SimpleCNN (自定义 4 层 CNN)",
                "short": "SimpleCNN",
                "init": "随机初始化 + 50 Epoch 训练",
                "test_acc": _BASELINE_ACC["simple_cnn"],
                "params": "2.6M",
                "color": "#F59E0B",
                "result": self._predict(self.simple_cnn, image),
            },
        ]
        return {"models": models_meta, "ground_truth_classes": self.classes}


compare_service = CompareService()
