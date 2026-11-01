"""The Ask contract: four outbound fields and an unmodified provider response."""
import json
from email.parser import BytesParser
from email import policy

import httpx
import pytest

from app.core.config import settings
from app.infrastructure.adapters.maira_assistant import MAIRA_ASK_URL, MAIRA_FILES_URL, MairaAssistant
from tests.conftest import csrf


@pytest.fixture()
def maira(monkeypatch):
    monkeypatch.setattr(settings, "maira_enabled", True)
    monkeypatch.setattr(settings, "maira_api_key", "test-api-key")
    monkeypatch.setattr(settings, "maira_project_key", "test-project-key")
    monkeypatch.setattr(settings, "maira_user_id", "configured-provider-user")
    monkeypatch.setattr(settings, "maira_gpt_profile_id", "configured-profile")
    # Legacy settings must never add fields to the provider request.
    monkeypatch.setattr(settings, "maira_dataset_id", "ignored-dataset")
    monkeypatch.setattr(settings, "maira_member_id", "ignored-member")
    return monkeypatch


def mock_maira(monkeypatch, status=200, body=b'{"detail":{"response":"Original answer","tokens":17,"references":[]}}'):
    captured = []
    original_client = httpx.Client
    def handle(request):
        uploaded = []
        if request.headers["content-type"].startswith("multipart/form-data"):
            message = BytesParser(policy=policy.default).parsebytes(
                ("Content-Type: " + request.headers["content-type"] + "\r\n\r\n").encode() + request.content
            )
            for part in message.iter_parts():
                field = part.get_param("name", header="content-disposition")
                if field == "payload":
                    payload = json.loads(part.get_payload(decode=True))
                else:
                    uploaded.append({"field": field, "filename": part.get_filename(), "content_type": part.get_content_type(), "content": part.get_payload(decode=True)})
        else:
            payload = json.loads(request.content)
        captured.append({"url": str(request.url), "headers": request.headers, "payload": payload, "files": uploaded})
        return httpx.Response(status, content=body, headers={"content-type": "application/json"})
    monkeypatch.setattr(httpx, "Client", lambda **kwargs: original_client(transport=httpx.MockTransport(handle), **kwargs))
    return captured


def test_exact_four_fields_and_unchanged_plain_query(maira):
    calls = mock_maira(maira)
    query = "is there any issue with LAND-BD-DEMO-0006"
    response = MairaAssistant().ask(query, history=[{"content": "old message"}], session_id="local-id")
    assert response.json()["detail"]["tokens"] == 17
    assert calls[0]["url"] == MAIRA_ASK_URL == "https://api.maira.gigalogy.com/client/v1/maira/ask"
    assert calls[0]["payload"] == {
        "user_id": "configured-provider-user", "query": query,
        "conversation_type": "question", "gpt_profile_id": "configured-profile",
    }
    assert calls[0]["headers"]["api-key"] == "test-api-key"
    assert calls[0]["headers"]["project-key"] == "test-project-key"


@pytest.mark.parametrize("with_file", [False, True])
def test_both_ask_endpoints_return_original_bytes_and_persist_history(authenticated_client, maira, with_file):
    body = b'{ "detail": {"response": "Original answer", "tokens": 17}, "other": [1,2] }'
    calls = mock_maira(maira, status=201, body=body)
    if with_file:
        response = authenticated_client.post(
            "/api/v1/chat/messages-with-files", headers=csrf(authenticated_client),
            data={"query": "Read this"}, files={"files": ("record.txt", b"synthetic document", "text/plain")},
        )
    else:
        response = authenticated_client.post("/api/v1/chat/messages", headers=csrf(authenticated_client), json={"query": "Read this"})
    assert response.status_code == 201, response.text
    assert response.content == body
    assert set(calls[0]["payload"]) == {"user_id", "query", "conversation_type", "gpt_profile_id"}
    assert calls[0]["payload"]["query"] == "Read this"
    if with_file:
        assert calls[0]["url"] == MAIRA_FILES_URL
        assert calls[0]["files"] == [{"field": "files", "filename": "record.txt", "content_type": "text/plain", "content": b"synthetic document"}]
    else:
        assert calls[0]["url"] == MAIRA_ASK_URL
        assert calls[0]["files"] == []
    conversation_id = response.headers["X-Conversation-ID"]
    history = authenticated_client.get(f"/api/v1/chat/conversations/{conversation_id}").json()
    assert history["messages"][-1]["content"] == "Original answer"
    assert history["messages"][0]["content"] == "Read this"
    assert history["id"] == conversation_id


@pytest.mark.parametrize("path", ["messages", "messages-with-files"])
def test_provider_error_body_and_status_are_preserved(authenticated_client, maira, tmp_path, path):
    body = b'{"detail":{"error":"provider rejected query"}}'
    mock_maira(maira, status=429, body=body)
    if path == "messages":
        response = authenticated_client.post(f"/api/v1/chat/{path}", headers=csrf(authenticated_client), json={"query": "Question"})
    else:
        response = authenticated_client.post(f"/api/v1/chat/{path}", headers=csrf(authenticated_client), data={"query": "Question"}, files={"files": ("sample.txt", b"record", "text/plain")})
    assert response.status_code == 429
    assert response.content == body
    assert authenticated_client.get("/api/v1/chat/conversations").json() == []
    assert not list((tmp_path / "uploads").glob("*"))


def test_old_content_field_is_rejected(authenticated_client):
    response = authenticated_client.post("/api/v1/chat/messages", headers=csrf(authenticated_client), json={"content": "old name"})
    assert response.status_code == 422


@pytest.mark.parametrize("filename, raw, mime", [
    ("khatian.pdf", b"%PDF-original-bytes-no-local-extraction", "application/pdf"),
    ("deed.png", b"original-image-bytes", "image/png"),
    ("record.txt", b"Mutation pending", "text/plain"),
    ("record.csv", b"land_id,status\nLAND-BD-DEMO-0006,pending", "text/csv"),
])
def test_files_forwarded_unchanged_without_touching_typed_query(maira, tmp_path, filename, raw, mime):
    path = tmp_path / filename
    path.write_bytes(raw)
    calls = mock_maira(maira)
    query = "Only the text I typed"
    MairaAssistant().ask(query, files=[{"path": str(path), "filename": filename}])
    assert calls[0]["url"] == MAIRA_FILES_URL
    assert calls[0]["payload"]["query"] == query
    assert len(calls[0]["payload"]) == 4
    assert calls[0]["files"] == [{"field": "files", "filename": filename, "content_type": mime, "content": raw}]


def test_file_only_request_keeps_query_empty(authenticated_client, maira):
    calls = mock_maira(maira)
    response = authenticated_client.post(
        "/api/v1/chat/messages-with-files", headers=csrf(authenticated_client),
        data={"query": ""}, files={"files": ("record.txt", b"original file bytes", "text/plain")},
    )
    assert response.status_code == 200, response.text
    assert calls[0]["payload"]["query"] == ""
    assert len(calls[0]["files"]) == 1


def test_missing_credentials_fail_before_network(monkeypatch):
    monkeypatch.setattr(settings, "maira_api_key", "")
    with pytest.raises(RuntimeError, match="MAIRA_API_KEY or MAIRA_PROJECT_KEY"):
        MairaAssistant().ask("Hi")
