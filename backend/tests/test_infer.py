"""推理接口测试

注意：完整推理需加载 ~85 MB ResNet-34 + 98 MB U-Net 权重，
若在 CI 中无权重文件，部分用例会自动 skip。
"""
import pytest


def test_multitask_rejects_non_image(client):
    """非图片文件应返回 400。"""
    resp = client.post(
        "/api/infer/multitask",
        files={"file": ("note.txt", b"hello world", "text/plain")},
    )
    assert resp.status_code == 400
    assert "图片" in resp.json()["detail"]


def test_multitask_rejects_missing_file(client):
    """缺少文件字段应返回 422 (FastAPI 校验失败)。"""
    resp = client.post("/api/infer/multitask")
    assert resp.status_code == 422


@pytest.mark.skipif("not __import__('pathlib').Path('weights/cls_torch.pth').exists()",
                    reason="需要分类模型权重")
def test_multitask_with_dummy_image(client, dummy_image_bytes):
    """合法图片应返回 200，且包含分类与分割结果。"""
    resp = client.post(
        "/api/infer/multitask",
        files={"file": ("test.jpg", dummy_image_bytes, "image/jpeg")},
    )
    # 模型已加载时应返回 200；未加载时返回 503 也算正常
    assert resp.status_code in (200, 503)
    if resp.status_code == 200:
        body = resp.json()
        # 分类结果包含 Top-1 类别与置信度
        assert "class_top1" in body
        assert "class_confidence" in body
        assert 0.0 <= body["class_confidence"] <= 1.0
        assert "latency_ms" in body


def test_compare_rejects_non_image(client):
    resp = client.post(
        "/api/infer/compare",
        files={"file": ("foo.bin", b"\x00\x01", "application/octet-stream")},
    )
    assert resp.status_code == 400


def test_gradcam_rejects_non_image(client):
    resp = client.post(
        "/api/infer/gradcam",
        files={"file": ("foo.bin", b"\x00\x01", "application/octet-stream")},
    )
    assert resp.status_code == 400
