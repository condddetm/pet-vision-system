from io import BytesIO
from PIL import Image
import numpy as np


def read_image_bytes(file_bytes: bytes) -> Image.Image:
    return Image.open(BytesIO(file_bytes)).convert("RGB")


def pil_to_numpy(img: Image.Image) -> np.ndarray:
    return np.array(img)
