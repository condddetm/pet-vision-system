"""错误反馈接口测试"""


def test_feedback_submit_valid(client):
    """合法反馈应返回 ok=True 与时间戳。"""
    payload = {
        "file_name": "pytest_sample.jpg",
        "predicted_breed": "Maine_Coon",
        "predicted_confidence": 0.81,
        "correct_breed": "Russian_Blue",
        "note": "pytest 自动化测试样本",
    }
    resp = client.post("/api/feedback", json=payload)
    assert resp.status_code == 200
    body = resp.json()
    assert body["ok"] is True
    assert "saved_at" in body


def test_feedback_rejects_invalid_confidence(client):
    """置信度超出 [0, 1] 范围应返回 422。"""
    payload = {
        "predicted_breed": "Maine_Coon",
        "predicted_confidence": 1.5,
        "correct_breed": "Russian_Blue",
    }
    resp = client.post("/api/feedback", json=payload)
    assert resp.status_code == 422


def test_feedback_recent_returns_list(client):
    """/recent 端点必须返回列表。"""
    resp = client.get("/api/feedback/recent?limit=5")
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


def test_feedback_stats_structure(client):
    """/stats 端点结构校验。"""
    resp = client.get("/api/feedback/stats")
    assert resp.status_code == 200
    body = resp.json()
    assert "total" in body
    assert "by_predicted" in body
    assert "by_correct" in body
    assert "top_confusions" in body
    assert isinstance(body["top_confusions"], list)
