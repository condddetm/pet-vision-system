import time
from typing import List, Tuple

import torch
import torch.nn as nn
import torchvision.transforms as T
from torchvision.models import resnet34
from PIL import Image

from app.core.config import WEIGHTS_DIR


class ClassifyService:
    def __init__(self) -> None:
        self.model_path = WEIGHTS_DIR / "cls_torch.pth"
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.model = None
        self.classes: List[str] = []
        self.img_size = 224
        self._load_model_if_exists()

    def _load_model_if_exists(self):
        if not self.model_path.exists():
            return

        ckpt = torch.load(self.model_path, map_location=self.device, weights_only=False)
        self.classes = ckpt.get("classes", [])
        self.img_size = int(ckpt.get("img_size", 224))

        model = resnet34(weights=None)
        model.fc = nn.Linear(model.fc.in_features, len(self.classes))
        model.load_state_dict(ckpt["model_state_dict"])
        model = model.to(self.device)
        model.eval()
        self.model = model

    def _fallback_predict(self) -> Tuple[str, float, List[dict]]:
        top5 = [{"label": "model_not_ready", "confidence": 1.0}]
        return "model_not_ready", 1.0, top5

    def predict(self, image: Image.Image) -> Tuple[str, float, List[dict], float]:
        t0 = time.perf_counter()

        if self.model is None or len(self.classes) == 0:
            top1_label, top1_conf, top5 = self._fallback_predict()
            latency = (time.perf_counter() - t0) * 1000
            return top1_label, top1_conf, top5, latency

        tf = T.Compose([
            T.Resize((self.img_size, self.img_size)),
            T.ToTensor(),
            T.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
        ])

        x = tf(image).unsqueeze(0).to(self.device)
        with torch.no_grad():
            logits = self.model(x)
            probs = torch.softmax(logits, dim=1)[0].detach().cpu().numpy().tolist()

        pairs = sorted(zip(self.classes, probs), key=lambda z: z[1], reverse=True)
        top1_label, top1_conf = pairs[0]
        top5 = [{"label": str(l), "confidence": round(float(c), 4)} for l, c in pairs[:5]]

        latency = (time.perf_counter() - t0) * 1000
        return str(top1_label), float(top1_conf), top5, latency


classify_service = ClassifyService()
