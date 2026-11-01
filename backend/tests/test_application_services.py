"""Service-level tests for application use cases, independent of HTTP routing."""
from __future__ import annotations

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.application.services import AuthService, ChatService
from app.domain.entities import Base
from app.infrastructure.adapters.demo_assistant import DemoAssistant
from app.infrastructure.unit_of_work import SqlAlchemyUnitOfWork


class FakePasswordHasher:
    """Fast deterministic test double; production hasher is tested separately."""
    def hash(self, password: str) -> str:
        return f"test-hash:{password}"
    def verify(self, password: str, password_hash: str) -> bool:
        return password_hash == self.hash(password)


class RecordingAssistant:
    def __init__(self):
        self.calls: list[dict] = []
    def respond(self, message, history):
        self.calls.append({"message": message, "history": history})
        return f"assistant reply to: {message}"
    def ask(self, message, history=None, files=None, session_id=None):
        self.calls.append({"message": message, "history": history or [], "files": files or [], "session_id": session_id})
        return f"assistant reply to: {message}"


@pytest.fixture()
def service_context():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    session = Session(engine, expire_on_commit=False)
    uow = SqlAlchemyUnitOfWork(session)
    auth = AuthService(uow, FakePasswordHasher())
    assistant = RecordingAssistant()
    chats = ChatService(uow, assistant)
    yield {"engine": engine, "session": session, "uow": uow, "auth": auth, "assistant": assistant, "chats": chats}
    session.close()
    Base.metadata.drop_all(engine)
    engine.dispose()


def create_user(auth):
    return auth.register({"full_name": "  Unit Test Citizen ", "email": "UNIT@example.com", "password": "TestPass123!"})


def test_auth_service_normalizes_email_and_prevents_duplicate(service_context):
    auth = service_context["auth"]
    user = create_user(auth)
    assert user.full_name == "Unit Test Citizen"
    assert user.email == "unit@example.com"
    with pytest.raises(ValueError, match="already exists"):
        create_user(auth)


def test_auth_service_authenticates_only_matching_password(service_context):
    auth = service_context["auth"]
    user = create_user(auth)
    assert auth.authenticate("UNIT@example.com", "TestPass123!").id == user.id
    with pytest.raises(PermissionError, match="incorrect"):
        auth.authenticate("unit@example.com", "incorrect")


def test_chat_service_persists_messages_and_supplies_recent_history(service_context):
    user = create_user(service_context["auth"])
    service = service_context["chats"]
    conversation, user_message, assistant_message, raw_response = service.send_message(user.id, "First question", None)
    assert user_message.sequence_no == 1
    assert assistant_message.sequence_no == 2
    assert len(service.get_conversation(conversation.id, user.id)[1]) == 2

    same_conversation, user_message_2, assistant_message_2, raw_response_2 = service.send_message(user.id, "Follow-up", conversation.id)
    assert same_conversation.id == conversation.id
    assert user_message_2.sequence_no == 3
    assert assistant_message_2.sequence_no == 4
    assistant = service_context["assistant"]
    assert assistant.calls[-1]["history"] == [
        {"role": "user", "content": "First question"},
        {"role": "assistant", "content": "assistant reply to: First question"},
    ]


def test_chat_service_passes_attachments_to_capable_provider(service_context, tmp_path):
    user = create_user(service_context["auth"])
    attachment = {"filename": "sample.pdf", "path": str(tmp_path / "sample.pdf"), "stored_name": "stored.pdf"}
    conversation, user_message, assistant_message, raw_response = service_context["chats"].send_message(
        user.id, "Describe the attachment", None, attachments=[attachment]
    )
    call = service_context["assistant"].calls[-1]
    assert call["files"] == [attachment]
    assert call["session_id"] == conversation.id
    assert user_message.content == "Describe the attachment"
    assert assistant_message.content == "assistant reply to: Describe the attachment"


def test_chat_service_rejects_blank_or_oversized_messages(service_context):
    user = create_user(service_context["auth"])
    service = service_context["chats"]
    with pytest.raises(ValueError, match="cannot be empty"):
        service.send_message(user.id, " \n ", None)
    with pytest.raises(ValueError, match="8,000"):
        service.send_message(user.id, "x" * 8001, None)


def test_chat_service_enforces_conversation_ownership(service_context):
    auth = service_context["auth"]
    owner = create_user(auth)
    other = auth.register({"full_name": "Other Citizen", "email": "other@example.com", "password": "OtherPass123!"})
    service = service_context["chats"]
    conversation, *_ = service.send_message(owner.id, "Private question", None)
    with pytest.raises(LookupError, match="not found"):
        service.get_conversation(conversation.id, other.id)
    with pytest.raises(LookupError, match="not found"):
        service.send_message(other.id, "Intrude", conversation.id)


def test_delete_conversation_removes_it_from_repository(service_context):
    user = create_user(service_context["auth"])
    service = service_context["chats"]
    conversation, *_ = service.send_message(user.id, "Delete me", None)
    service.delete_conversation(conversation.id, user.id)
    assert service.list_conversations(user.id) == []
    with pytest.raises(LookupError):
        service.get_conversation(conversation.id, user.id)
