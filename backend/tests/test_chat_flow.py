from tests.conftest import csrf, register_and_login


def send(client, query, conversation_id=None):
    headers = csrf(client)
    if conversation_id:
        headers["X-Conversation-ID"] = conversation_id
    return client.post("/api/v1/chat/messages", headers=headers, json={"query": query})


def test_auth_and_chat_history_is_persisted(client):
    register_and_login(client)
    response = send(client, "How can I understand a Khatian?")
    assert response.status_code == 200, response.text
    assert isinstance(response.json(), str)  # Demo provider response is a string.
    conversation_id = response.headers["X-Conversation-ID"]
    detail = client.get(f"/api/v1/chat/conversations/{conversation_id}").json()
    assert len(detail["messages"]) == 2
    assert detail["messages"][0]["content"] == "How can I understand a Khatian?"
    assert "prototype" in detail["messages"][1]["content"].lower()
    assert client.get("/api/v1/chat/conversations").json()[0]["id"] == conversation_id


def test_users_cannot_read_or_extend_another_users_conversation(client):
    register_and_login(client)
    conversation_id = send(client, "Keep this private").headers["X-Conversation-ID"]
    client.post("/api/auth/logout", headers=csrf(client))
    register_and_login(client, email="other@example.com", password="AnotherPass123!")
    assert client.get(f"/api/v1/chat/conversations/{conversation_id}").status_code == 404
    assert send(client, "Intrude", conversation_id).status_code == 404


def test_cache_is_invalidated_after_chat_updates_and_deletes(client):
    register_and_login(client)
    assert client.get("/api/v1/chat/conversations").json() == []
    first = send(client, "First message")
    assert first.status_code == 200
    conversation_id = first.headers["X-Conversation-ID"]
    assert client.get("/api/v1/chat/conversations").json()[0]["id"] == conversation_id
    assert len(client.get(f"/api/v1/chat/conversations/{conversation_id}").json()["messages"]) == 2
    assert send(client, "A follow-up", conversation_id).status_code == 200
    updated = client.get(f"/api/v1/chat/conversations/{conversation_id}").json()
    assert len(updated["messages"]) == 4
    assert updated["messages"][-2]["content"] == "A follow-up"
    assert client.delete(f"/api/v1/chat/conversations/{conversation_id}", headers=csrf(client)).status_code == 204
    assert client.get("/api/v1/chat/conversations").json() == []
    assert client.get(f"/api/v1/chat/conversations/{conversation_id}").status_code == 404


def test_empty_and_overlong_messages_are_rejected(authenticated_client):
    assert send(authenticated_client, "   ").status_code == 422
    assert send(authenticated_client, "x" * 8001).status_code == 422
