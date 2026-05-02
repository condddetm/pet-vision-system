from pathlib import Path

import numpy as np
from PIL import Image
import torch
import torchvision.transforms as T
import segmentation_models_pytorch as smp

from app.core.config import WEIGHTS_DIR


class SegmentService:
    def __init__(self):
        self.model_path = WEIGHTS_DIR / "seg_unet.pth"
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.img_size = 256
        self.model = self._build_model()
        self._load_model_if_exists()
        self.tf = T.Compose([
            T.Resize((self.img_size, self.img_size)),
            T.ToTensor(),
        ])

    def _build_model(self):
        model = smp.Unet(
            encoder_name="resnet34",
            encoder_weights=None,
            in_channels=3,
            classes=1,
        ).to(self.device)
        model.eval()
        return model

    def _load_model_if_exists(self):
        if self.model_path.exists():
            state = torch.load(self.model_path, map_location=self.device, weights_only=False)
            self.model.load_state_dict(state)
            self.model.eval()

    def _fallback_predict(self, image: Image.Image) -> np.ndarray:
        arr = np.array(image.convert("RGB"))
        gray = arr.mean(axis=2)
        thr = np.percentile(gray, 55)
        return (gray < thr).astype(np.float32)

    def predict_mask(self, image: Image.Image) -> np.ndarray:
        if not self.model_path.exists():
            return self._fallback_predict(image)

        x = self.tf(image).unsqueeze(0).to(self.device)
        with torch.no_grad():
            logits = self.model(x)
            prob = torch.sigmoid(logits)[0, 0].detach().cpu().numpy()

        mask = (prob > 0.5).astype(np.float32)
        return mask


segment_service = SegmentService()
