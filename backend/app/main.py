import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

from app.core.config import TMP_DIR, ARTIFACTS_DIR
from app.core.rate_limit import limiter
from app.routers.infer import router as infer_router
from app.routers.dataset import router as dataset_router
from app.routers.metrics import router as metrics_router
from app.routers.feedback import router as feedback_router
from app.routers.ws_infer import router as ws_infer_router

app = FastAPI(
    title="Pet MultiTask System API",
    version="1.0.0",
    description="基于深度学习的智能宠物视觉信息系统：图像分类 + 图像分割 + Grad-CAM 可解释性",
)

# 限流：保护推理与反馈接口免受瞬时高并发冲击
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(SlowAPIMiddleware)

# CORS：默认仅允许本地开发端口；生产环境通过环境变量 ALLOWED_ORIGINS 覆盖（逗号分隔）。
_default_origins = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "http://localhost:4173",  # vite preview
    "http://127.0.0.1:4173",
]
_env_origins = os.getenv("ALLOWED_ORIGINS", "").strip()
allowed_origins = (
    [o.strip() for o in _env_origins.split(",") if o.strip()]
    if _env_origins
    else _default_origins
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(infer_router)
app.include_router(dataset_router)
app.include_router(metrics_router)
app.include_router(feedback_router)
app.include_router(ws_infer_router)

TMP_DIR.mkdir(exist_ok=True)
(ARTIFACTS_DIR / "classification").mkdir(parents=True, exist_ok=True)
(ARTIFACTS_DIR / "segmentation").mkdir(parents=True, exist_ok=True)

app.mount("/static", StaticFiles(directory=str(TMP_DIR)), name="static")
app.mount("/artifacts", StaticFiles(directory=str(ARTIFACTS_DIR)), name="artifacts")


@app.get("/")
def health():
    return {"message": "Backend is running"}
