from __future__ import annotations

from unittest.mock import AsyncMock, patch

from app.services.llm.base import ChatResponse


def _mock_llm_chat(*args, **kwargs):
    """返回一个 mock 的 ChatResponse"""
    return ChatResponse(
        content="你好！有什么可以帮您的吗？",
        model="gpt-4o-mini",
        finish_reason="stop",
        prompt_tokens=20,
        completion_tokens=15,
        total_tokens=35,
    )


async def _mock_llm_stream(*args, **kwargs):
    """返回一个 mock 的流式响应"""
    from app.services.llm.base import ChatDelta

    for text in ["你好", "！有什么", "可以帮您的吗？"]:
        yield ChatDelta(content=text, finish_reason=None)
    yield ChatDelta(content="", finish_reason="stop")


def _create_session(client) -> str:
    resp = client.post(
        "/api/v1/sessions",
        json={
            "tenant_code": "demo_tenant",
            "channel": "demo",
            "external_user_id": "u_10001",
        },
    )
    return resp.json()["data"]["session_code"]


@patch("app.services.conversation.orchestrator.get_llm_provider")
def test_chat_sync(mock_get_provider, client):
    mock_provider = AsyncMock()
    mock_provider.chat = AsyncMock(side_effect=_mock_llm_chat)
    mock_get_provider.return_value = mock_provider

    session_code = _create_session(client)

    response = client.post(
        "/api/v1/chat",
        json={
            "tenant_code": "demo_tenant",
            "session_code": session_code,
            "message": {"type": "text", "content": "你好"},
            "stream": False,
        },
    )

    body = response.json()
    assert response.status_code == 200
    assert body["code"] == 0
    assert body["data"]["role"] == "assistant"
    assert body["data"]["content"] == "你好！有什么可以帮您的吗？"
    assert body["data"]["finish_reason"] == "stop"
    assert body["data"]["message_code"].startswith("m_")


@patch("app.services.conversation.orchestrator.get_llm_provider")
def test_chat_stream(mock_get_provider, client):
    mock_provider = AsyncMock()
    mock_provider.chat_stream = _mock_llm_stream
    mock_get_provider.return_value = mock_provider

    session_code = _create_session(client)

    response = client.post(
        "/api/v1/chat",
        json={
            "tenant_code": "demo_tenant",
            "session_code": session_code,
            "message": {"type": "text", "content": "你好"},
            "stream": True,
        },
    )

    assert response.status_code == 200
    assert "text/event-stream" in response.headers["content-type"]

    text = response.text
    assert "event: start" in text
    assert "event: delta" in text
    assert "event: done" in text


@patch("app.services.conversation.orchestrator.get_llm_provider")
def test_chat_session_not_found(mock_get_provider, client):
    mock_provider = AsyncMock()
    mock_get_provider.return_value = mock_provider

    # Create tenant via session creation
    _create_session(client)

    response = client.post(
        "/api/v1/chat",
        json={
            "tenant_code": "demo_tenant",
            "session_code": "s_not_exists",
            "message": {"type": "text", "content": "你好"},
            "stream": False,
        },
    )

    assert response.status_code == 404
    assert response.json()["message"] == "session not found"


def test_chat_message_too_long(client):
    session_code = _create_session(client)

    response = client.post(
        "/api/v1/chat",
        json={
            "tenant_code": "demo_tenant",
            "session_code": session_code,
            "message": {"type": "text", "content": "x" * 5000},
            "stream": False,
        },
    )

    # Schema validation catches max_length=4000
    assert response.status_code == 422


@patch("app.services.conversation.orchestrator.get_llm_provider")
def test_chat_creates_assistant_message_in_db(mock_get_provider, client):
    """验证同步问答后 assistant 消息写入数据库，可通过历史接口查询"""
    mock_provider = AsyncMock()
    mock_provider.chat = AsyncMock(side_effect=_mock_llm_chat)
    mock_get_provider.return_value = mock_provider

    session_code = _create_session(client)

    client.post(
        "/api/v1/chat",
        json={
            "tenant_code": "demo_tenant",
            "session_code": session_code,
            "message": {"type": "text", "content": "你好"},
            "stream": False,
        },
    )

    # 查历史
    history_resp = client.get(f"/api/v1/sessions/{session_code}/messages")
    body = history_resp.json()

    assert body["code"] == 0
    assert body["data"]["total"] == 2  # user + assistant
    assert body["data"]["items"][0]["role"] == "user"
    assert body["data"]["items"][1]["role"] == "assistant"
    assert body["data"]["items"][1]["content"] == "你好！有什么可以帮您的吗？"


@patch("app.services.conversation.orchestrator.get_llm_provider")
def test_chat_multi_turn(mock_get_provider, client):
    """验证多轮对话上下文传递"""
    mock_provider = AsyncMock()
    call_count = 0

    async def _mock_chat_with_context(request):
        nonlocal call_count
        call_count += 1
        # 第二轮应该包含之前的对话历史
        if call_count == 2:
            # messages 包含 system + 第一轮 user + 第一轮 assistant + 第二轮 user
            assert len(request.messages) >= 4
        return ChatResponse(
            content=f"回复第{call_count}轮",
            model="gpt-4o-mini",
            finish_reason="stop",
            prompt_tokens=20,
            completion_tokens=10,
            total_tokens=30,
        )

    mock_provider.chat = AsyncMock(side_effect=_mock_chat_with_context)
    mock_get_provider.return_value = mock_provider

    session_code = _create_session(client)

    # 第一轮
    client.post(
        "/api/v1/chat",
        json={
            "tenant_code": "demo_tenant",
            "session_code": session_code,
            "message": {"type": "text", "content": "第一个问题"},
            "stream": False,
        },
    )

    # 第二轮
    resp2 = client.post(
        "/api/v1/chat",
        json={
            "tenant_code": "demo_tenant",
            "session_code": session_code,
            "message": {"type": "text", "content": "第二个问题"},
            "stream": False,
        },
    )

    assert resp2.json()["data"]["content"] == "回复第2轮"
    assert call_count == 2
