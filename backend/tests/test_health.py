"""健康检查与基础路由测试"""


def test_health_root(client):
    """GET / 应返回 200 + 包含 'running' 字样。"""
    resp = client.get("/")
    assert resp.status_code == 200
    body = resp.json()
    assert "message" in body
    assert "running" in body["message"].lower()


def test_openapi_docs_available(client):
    """OpenAPI Schema 必须可访问，证明路由注册成功。"""
    resp = client.get("/openapi.json")
    assert resp.status_code == 200
    schema = resp.json()
    paths = schema.get("paths", {})

    # 关键端点必须存在
    assert "/api/infer/multitask" in paths
    assert "/api/infer/compare" in paths
    assert "/api/infer/gradcam" in paths
    assert "/api/feedback" in paths
    assert "/api/dataset/stats" in paths
    assert "/api/metrics/summary" in paths


def test_swagger_ui_available(client):
    """/docs Swagger UI 应可访问。"""
    resp = client.get("/docs")
    assert resp.status_code == 200
    assert "text/html" in resp.headers.get("content-type", "")
