"""
pytest 共享 fixture

提供 TestClient 实例与示例图片字节流，给所有测试用例复用。
"""
from __future__ import annotations

import io
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from PIL import Image

from app.main import app


@pytest.fixture(scope="session")
def client() -> TestClient:
    """FastAPI 测试客户端，启动一次即可在整个 session 复用。"""
    return TestClient(app)


@pytest.fixture
def dummy_image_bytes() -> bytes:
    """生成一张 224×224 RGB 测试图片（纯红色）。"""
    img = Image.new("RGB", (224, 224), color=(220, 80, 80))
    buf = io.BytesIO()
    img.save(buf, format="JPEG")
    return buf.getvalue()


@pytest.fixture
def real_sample_image() -> bytes | None:
    """优先使用项目内置样例图，便于做端到端推理验证。"""
    candidates = [
        Path(__file__).resolve().parents[2] / "frontend" / "public" / "samples" / "samoyed.jpg",
        Path(__file__).resolve().parents[2] / "frontend" / "public" / "samples" / "beagle.jpg",
    ]
    for path in candidates:
        if path.exists():
            return path.read_bytes()
    return None
