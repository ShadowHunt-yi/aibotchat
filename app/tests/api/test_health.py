def test_health(client):
    response = client.get("/api/v1/health")

    assert response.status_code == 200
    assert response.json() == {
        "code": 0,
        "message": "ok",
        "data": {"status": "ok"},
        "trace_id": None,
    }
    assert response.headers["X-Trace-Id"].startswith("trace_")
