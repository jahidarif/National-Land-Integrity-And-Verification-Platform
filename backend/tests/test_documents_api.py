from tests.conftest import csrf, register_and_login


def test_user_document_upload_view_delete_and_private_scope(client, monkeypatch):
    import app.presentation.documents_router as documents_router
    uploaded = []
    deleted = []
    class FakeUploader:
        def upload(self, storage_key, content, content_type):
            uploaded.append((storage_key, content, content_type))
    class FakeDeleter:
        def delete(self, storage_key):
            deleted.append(storage_key)
    class FakeSigner:
        def sign(self, storage_key, filename, content_type):
            return "https://private.example/presigned"
    monkeypatch.setattr(documents_router, "S3DocumentUploader", FakeUploader)
    monkeypatch.setattr(documents_router, "S3DocumentDeleter", FakeDeleter)
    monkeypatch.setattr(documents_router, "S3DocumentUrlSigner", FakeSigner)
    register_and_login(client)
    response = client.post("/api/user/documents", files={"file":("proof.txt",b"synthetic evidence","text/plain")}, headers=csrf(client))
    assert response.status_code == 201, response.text
    document = response.json()
    assert document["fileName"] == "proof.txt"
    assert "storage_key" not in document
    assert uploaded and uploaded[0][1] == b"synthetic evidence"
    listing = client.get("/api/user/documents")
    assert listing.status_code == 200 and listing.json()["totalCount"] == 1
    url = client.get(f"/api/user/documents/{document['id']}/url")
    assert url.status_code == 200 and url.json()["url"] == "https://private.example/presigned"
    client.post("/api/auth/logout", json={}, headers=csrf(client))
    client.post("/api/auth/register", json={"full_name":"Another User","email":"another@example.com","password":"SafePass123!","role":"User"}, headers=csrf(client))
    client.post("/api/auth/login", json={"email":"another@example.com","password":"SafePass123!"}, headers=csrf(client))
    assert client.get(f"/api/user/documents/{document['id']}/url").status_code == 404
    assert client.delete(f"/api/user/documents/{document['id']}",headers=csrf(client)).status_code == 404
    client.post("/api/auth/logout", json={}, headers=csrf(client))
    client.post("/api/auth/login", json={"email":"citizen@example.com","password":"SafePass123!"}, headers=csrf(client))
    removed = client.delete(f"/api/user/documents/{document['id']}",headers=csrf(client))
    assert removed.status_code == 204
    assert deleted


def test_user_can_attach_only_selected_stored_document_to_chat(client, monkeypatch, tmp_path):
    import httpx
    import app.presentation.chat_router as chat_router
    from types import SimpleNamespace
    from app.domain.models import Document
    from app.infrastructure.database import get_db
    from app.presentation.deps import get_chat_service
    register_and_login(client, email="chat-owner@example.com")
    db_gen = client.app.dependency_overrides[get_db]()
    db = next(db_gen)
    user = db.query(__import__("app.domain.models", fromlist=["User"]).User).filter_by(email="chat-owner@example.com").first()
    document = Document(id="stored-document", user_id=user.id, original_filename="chosen.txt", content_type="text/plain", size_bytes=12, storage_key=f"users/{user.id}/documents/stored-document/chosen.txt", checksum_sha256="0"*64)
    db.add(document); db.commit(); db_gen.close()
    class FakeReader:
        def read(self, storage_key):
            assert storage_key.endswith("chosen.txt")
            return b"chosen text!"
    captured = {}
    class FakeChatService:
        def send_message(self, user_id, content, conversation_id, attachments=None):
            captured["user_id"] = user_id; captured["content"] = content; captured["attachments"] = attachments
            return SimpleNamespace(id="conv-selected"), None, None, httpx.Response(200, json={"answer":"ok"})
    monkeypatch.setattr(chat_router, "S3DocumentReader", FakeReader)
    client.app.dependency_overrides[get_chat_service] = lambda: FakeChatService()
    try:
        response = client.post("/api/v1/chat/messages-with-files", data={"query":"Summarize this" ,"document_ids":["stored-document"]}, files={"files":("local.txt",b"local file","text/plain")}, headers=csrf(client))
        assert response.status_code == 200, response.text
        assert captured["content"] == "Summarize this"
        assert len(captured["attachments"]) == 2
        from pathlib import Path
        stored_attachment = next(item for item in captured["attachments"] if item["filename"] == "chosen.txt")
        local_attachment = next(item for item in captured["attachments"] if item["filename"] == "local.txt")
        assert Path(stored_attachment["path"]).exists() is False
        assert Path(local_attachment["path"]).exists() is True
    finally:
        client.app.dependency_overrides.pop(get_chat_service, None)
