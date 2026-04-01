def test_create_session(client):
    response = client.post(
        "/api/v1/sessions",
        json={
            "tenant_code": "demo_tenant",
            "channel": "demo",
            "external_user_id": "u_10001",
            "metadata": {"device_id": "d_001"},
        },
    )

    body = response.json()

    assert response.status_code == 201
    assert body["code"] == 0
    assert body["message"] == "ok"
    assert body["data"]["session_code"].startswith("s_")
    assert body["data"]["status"] == "active"


def test_create_session_requires_fields(client):
    response = client.post("/api/v1/sessions", json={"tenant_code": "demo_tenant"})

    assert response.status_code == 422
    assert response.json()["message"] == "validation error"
