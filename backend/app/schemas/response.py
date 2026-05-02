from pydantic import BaseModel
from typing import List


class TopKItem(BaseModel):
    label: str
    confidence: float


class MultitaskInferResponse(BaseModel):
    class_top1: str
    class_confidence: float
    top5: List[TopKItem]
    mask_url: str
    overlay_url: str
    pet_area_ratio: float
    gradcam_url: str = ""
    latency_ms: float
