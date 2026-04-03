from __future__ import annotations


def _create_session_and_message(client) -> str:
    session_resp = client.post(
        "/api/v1/sessions",
        json={
            "tenant_code": "demo_tenant",
            "channel": "demo",
            "external_user_id": "u_10001",
        },
    )
    session_code = session_resp.json()["data"]["session_code"]

    client.post(
        "/api/v1/messages",
        json={
            "tenant_code": "demo_tenant",
            "session_code": session_code,
            "message": {"type": "text", "content": "你好"},
        },
    )
    return session_code


def test_get_session_messages(client):
    session_code = _create_session_and_message(client)

    response = client.get(f"/api/v1/sessions/{session_code}/messages")
    body = response.json()

    assert response.status_code == 200
    assert body["code"] == 0
    assert body["data"]["session_code"] == session_code
    assert body["data"]["total"] == 1
    assert body["data"]["items"][0]["role"] == "user"
    assert body["data"]["items"][0]["content"] == "你好"


def test_get_session_messages_not_found(client):
    response = client.get("/api/v1/sessions/s_not_exists/messages")
    assert response.status_code == 404


def test_get_session_messages_pagination(client):
    session_resp = client.post(
        "/api/v1/sessions",
        json={
            "tenant_code": "demo_tenant",
            "channel": "demo",
            "external_user_id": "u_10001",
        },
    )
    session_code = session_resp.json()["data"]["session_code"]

    # 发送 3 条消息
    for i in range(3):
        client.post(
            "/api/v1/messages",
            json={
                "tenant_code": "demo_tenant",
                "session_code": session_code,
                "message": {"type": "text", "content": f"消息{i}"},
            },
        )

    # limit=2, offset=0
    resp = client.get(f"/api/v1/sessions/{session_code}/messages?limit=2&offset=0")
    body = resp.json()
    assert body["data"]["total"] == 3
    assert len(body["data"]["items"]) == 2

    # offset=2
    resp = client.get(f"/api/v1/sessions/{session_code}/messages?limit=2&offset=2")
    body = resp.json()
    assert len(body["data"]["items"]) == 1
