import uuid
import cv2
import numpy as np
from PIL import Image

from app.core.config import TMP_DIR


def save_mask_and_overlay(rgb_image: np.ndarray, mask: np.ndarray) -> tuple[str, str, float]:
    uid = uuid.uuid4().hex[:10]

    # 将 mask 缩放到与原图相同尺寸（模型输出 256×256，原图可能任意尺寸）
    h, w = rgb_image.shape[:2]
    if mask.shape != (h, w):
        mask = np.array(
            Image.fromarray((mask * 255).astype(np.uint8)).resize((w, h), Image.NEAREST)
        ) / 255.0

    mask_bin = (mask > 0.5).astype(np.uint8)

    mask_path    = TMP_DIR / f"mask_{uid}.png"
    overlay_path = TMP_DIR / f"overlay_{uid}.png"

    mask_img = (mask_bin * 255).astype(np.uint8)
    Image.fromarray(mask_img).save(mask_path)

    color_mask = np.zeros_like(rgb_image)
    color_mask[:, :, 1] = mask_img
    overlay = cv2.addWeighted(rgb_image, 0.7, color_mask, 0.3, 0)
    Image.fromarray(overlay).save(overlay_path)

    ratio = float(mask_bin.sum() / mask_bin.size)
    return f"/static/{mask_path.name}", f"/static/{overlay_path.name}", ratio
