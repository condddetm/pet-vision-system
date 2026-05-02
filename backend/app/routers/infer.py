from fastapi import APIRouter, UploadFile, File, HTTPException, Request

from app.core.rate_limit import limiter, INFER_RATE
from app.schemas.response import MultitaskInferResponse
from app.utils.image_io import read_image_bytes
from app.services.multitask_service import multitask_service
from app.services.compare_service import compare_service
from app.services.classify_service import classify_service
from app.services.gradcam_service import gradcam_service

router = APIRouter(prefix="/api/infer", tags=["infer"])


@router.post("/multitask", response_model=MultitaskInferResponse)
@limiter.limit(INFER_RATE)
async def multitask_infer(request: Request, file: UploadFile = File(...)):
    if not file.content_type or not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="请上传图片文件")

    data = await file.read()
    image = read_image_bytes(data)
    result = multitask_service.infer(image)
    return result


@router.post("/compare")
@limiter.limit(INFER_RATE)
async def compare_infer(request: Request, file: UploadFile = File(...)):
    """对同一张图片调用三个分类模型并返回对比结果"""
    if not file.content_type or not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="请上传图片文件")

    data = await file.read()
    image = read_image_bytes(data)
    return compare_service.infer_all(image)


@router.post("/gradcam")
@limiter.limit(INFER_RATE)
async def gradcam_infer(request: Request, file: UploadFile = File(...)):
    """对一张图片生成 Grad-CAM 热力图叠加 (基于 ResNet-34 layer4)"""
    if not file.content_type or not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="请上传图片文件")
    if classify_service.model is None:
        raise HTTPException(status_code=503, detail="分类模型尚未加载")

    data = await file.read()
    image = read_image_bytes(data)

    url = gradcam_service.generate(
        model=classify_service.model,
        image=image,
        img_size=classify_service.img_size,
    )
    return {
        "available": bool(url),
        "heatmap_url": url,
        "target_layer": "layer4[-1]",
        "model": "ResNet-34",
    }
