import time
from PIL import Image
import numpy as np

from app.services.classify_service import classify_service
from app.services.segment_service import segment_service
from app.services.gradcam_service import gradcam_service
from app.utils.visualize import save_mask_and_overlay


class MultitaskService:
    def infer(self, image: Image.Image) -> dict:
        t0 = time.perf_counter()
        top1_label, top1_conf, top5, _ = classify_service.predict(image)

        mask = segment_service.predict_mask(image)
        rgb = np.array(image.convert("RGB"))
        mask_url, overlay_url, ratio = save_mask_and_overlay(rgb, mask)

        gradcam_url = ""
        try:
            if classify_service.model is not None:
                gradcam_url = gradcam_service.generate(
                    classify_service.model, image, img_size=classify_service.img_size
                )
        except Exception:
            gradcam_url = ""

        total_latency = (time.perf_counter() - t0) * 1000
        return {
            "class_top1": top1_label,
            "class_confidence": round(top1_conf, 4),
            "top5": top5,
            "mask_url": mask_url,
            "overlay_url": overlay_url,
            "pet_area_ratio": round(ratio, 4),
            "gradcam_url": gradcam_url,
            "latency_ms": round(total_latency, 2),
        }


multitask_service = MultitaskService()
