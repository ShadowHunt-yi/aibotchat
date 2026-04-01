def test_create_message(client):
    session_response = client.post(
        "/api/v1/sessions",
        json={
            "tenant_code": "demo_tenant",
            "channel": "demo",
            "external_user_id": "u_10001",
        },
    )
    session_code = session_response.json()["data"]["session_code"]

    response = client.post(
        "/api/v1/messages",
        json={
            "tenant_code": "demo_tenant",
            "session_code": session_code,
            "message": {"type": "text", "content": "你好"},
            "request_id": "req_001",
        },
    )

    body = response.json()

    assert response.status_code == 202
    assert body["code"] == 0
    assert body["data"]["message_code"].startswith("m_")
    assert body["data"]["role"] == "user"
    assert body["data"]["status"] == "accepted"


def test_create_message_with_missing_session(client):
    client.post(
        "/api/v1/sessions",
        json={
            "tenant_code": "demo_tenant",
            "channel": "demo",
            "external_user_id": "u_10001",
        },
    )

    response = client.post(
        "/api/v1/messages",
        json={
            "tenant_code": "demo_tenant",
            "session_code": "s_not_exists",
            "message": {"type": "text", "content": "你好"},
        },
    )

    assert response.status_code == 404
    assert response.json()["message"] == "session not found"
