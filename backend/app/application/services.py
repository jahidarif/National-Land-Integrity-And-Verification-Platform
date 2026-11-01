from __future__ import annotations

import secrets
import json
import httpx
import uuid
from datetime import datetime, timedelta, timezone

from app.domain.ports.i_password_hasher import IPasswordHasher
from app.domain.ports.i_password_verifier import IPasswordVerifier
from app.core.config import settings
from app.infrastructure.adapters.maira_assistant import extract_response_text
from app.core.security import decode_token, make_token
from app.domain.entities import (
    Conversation, Message, RefreshToken, User, Role,
)
from app.domain.repositories import IUnitOfWork


class AuthService:
    def __init__(
        self,
        uow: IUnitOfWork,
        password_hasher: IPasswordHasher,
        password_verifier: IPasswordVerifier | None = None,
    ):
        self.uow = uow
        self.password_hasher = password_hasher
        self.password_verifier = password_verifier or password_hasher

    def register(self, data: dict) -> User:
        email = data["email"].strip().lower()

        if self.uow.users.get_by_email(email):
            raise ValueError(
                "An account with this email already exists"
            )

        user = User(
            id=str(uuid.uuid4()),
            full_name=data["full_name"].strip(),
            email=email,
            password_hash=self.password_hasher.hash(
                data["password"]
            ),
            role=Role(data.get("role", "User")),
            is_active=True,
        )

        self.uow.users.add(user)
        self.uow.commit()
        self.uow.refresh(user)
        return user

    def authenticate(self, email: str, password: str) -> User:
        user = self.uow.users.get_by_email(
            email.strip().lower()
        )

        if (
            not user
            or not user.is_active
            or not self.password_verifier.verify(
                password,
                user.password_hash,
            )
        ):
            raise PermissionError(
                "Email or password is incorrect"
            )

        return user

    def _token_pair(
        self,
        user: User,
    ) -> tuple[str, str, RefreshToken]:
        jti = secrets.token_urlsafe(32)
        refresh_lifetime = timedelta(
            days=settings.jwt_refresh_days
        )

        access = make_token(
            user.id,
            user.email,
            user.full_name,
            "access",
            timedelta(minutes=settings.jwt_access_minutes),
        )

        refresh = make_token(
            user.id,
            user.email,
            user.full_name,
            "refresh",
            refresh_lifetime,
            jti=jti,
        )

        row = RefreshToken(
            id=str(uuid.uuid4()),
            user_id=user.id,
            jti=jti,
            expires_at=(
                datetime.now(timezone.utc) + refresh_lifetime
            ),
        )

        return access, refresh, row

    def tokens(self, user: User) -> tuple[str, str]:
        access, refresh, row = self._token_pair(user)

        self.uow.refresh_tokens.add(row)
        self.uow.commit()

        return access, refresh

    def current_user(self, access_token: str) -> User:
        try:
            claims = decode_token(access_token, "access")
        except ValueError as exc:
            raise PermissionError(str(exc)) from exc

        user = self.uow.users.get_by_id(str(claims["sub"]))

        if not user or not user.is_active:
            raise PermissionError(
                "Account is not available"
            )

        return user

    def refresh(
        self,
        refresh_token: str,
    ) -> tuple[User, str, str]:
        try:
            claims = decode_token(refresh_token, "refresh")
        except ValueError as exc:
            raise PermissionError(str(exc)) from exc

        row = self.uow.refresh_tokens.get_by_jti(
            str(claims.get("jti", ""))
        )
        now = datetime.now(timezone.utc)

        if (
            not row
            or row.revoked_at is not None
            or _as_utc(row.expires_at) <= now
        ):
            raise PermissionError(
                "Invalid or expired refresh token"
            )

        user = self.uow.users.get_by_id(str(claims["sub"]))

        if not user or not user.is_active:
            raise PermissionError(
                "Account is not available"
            )

        row.revoked_at = now
        access, refresh, new_row = self._token_pair(user)

        self.uow.refresh_tokens.add(new_row)
        self.uow.commit()

        return user, access, refresh

    def logout(self, refresh_token: str | None) -> None:
        if not refresh_token:
            return

        try:
            claims = decode_token(refresh_token, "refresh")
        except ValueError:
            return

        row = self.uow.refresh_tokens.get_by_jti(
            str(claims.get("jti", ""))
        )

        if row and row.revoked_at is None:
            row.revoked_at = datetime.now(timezone.utc)
            self.uow.commit()


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)

    return value.astimezone(timezone.utc)


class ChatService:
    def __init__(
        self,
        uow: IUnitOfWork,
        assistant: object,
    ):
        self.uow = uow
        self.assistant = assistant

    def list_conversations(
        self,
        user_id: str,
    ) -> list[Conversation]:
        return self.uow.conversations.list_for_user(
            user_id,
            limit=100,
        )

    def get_conversation(
        self,
        conversation_id: str,
        user_id: str,
    ) -> tuple[Conversation, list[Message]]:
        conversation = self.uow.conversations.get_for_user(
            conversation_id,
            user_id,
        )

        if not conversation:
            raise LookupError("Conversation not found")

        return (
            conversation,
            self.uow.messages.list_for_conversation(
                conversation_id
            ),
        )

    def send_message(
        self,
        user_id: str,
        content: str,
        conversation_id: str | None,
        attachments: list[dict] | None = None,
    ) -> tuple[Conversation, Message, Message, object]:
        message_text = content.strip()

        if not message_text and not attachments:
            raise ValueError("Message cannot be empty")

        if len(message_text) > 8000:
            raise ValueError(
                "Message must be 8,000 characters or fewer"
            )

        conversation = None

        if conversation_id:
            conversation = self.uow.conversations.get_for_user(
                conversation_id,
                user_id,
            )

            if not conversation:
                raise LookupError("Conversation not found")

        if conversation is None:
            title = message_text.replace("\n", " ").strip()

            if len(title) > 58:
                title = title[:55].rstrip() + "..."

            conversation = Conversation(
                id=str(uuid.uuid4()),
                user_id=user_id,
                user_email=self.uow.users.get_by_id(user_id).email,
                title=title or "New conversation",
            )

            self.uow.conversations.add(conversation)
            self.uow.flush()

        history_rows = self.uow.messages.list_for_conversation(
            conversation.id
        )

        history = [
            {
                "role": row.role,
                "content": row.content,
            }
            for row in history_rows[-12:]
        ]

        user_message = Message(
            id=str(uuid.uuid4()),
            conversation_id=conversation.id,
            role="user",
            content=message_text,
            sequence_no=len(history_rows) + 1,
        )

        ask_method = getattr(self.assistant, "ask", None)

        if callable(ask_method):
            provider_response = ask_method(
                message_text,
                history=history,
                files=attachments or [],
                session_id=conversation.id,
            )
        else:
            provider_response = self.assistant.respond(
                message_text,
                history,
            )

        if isinstance(provider_response, httpx.Response):
            try:
                payload = provider_response.json()
                assistant_text = extract_response_text(payload) or json.dumps(payload, ensure_ascii=False)
            except ValueError:
                assistant_text = provider_response.text
        else:
            assistant_text = str(provider_response)

        assistant_message = Message(
            id=str(uuid.uuid4()),
            conversation_id=conversation.id,
            role="assistant",
            content=assistant_text,
            sequence_no=len(history_rows) + 2,
        )

        self.uow.messages.add(user_message)
        self.uow.messages.add(assistant_message)

        conversation.updated_at = datetime.now(timezone.utc)

        self.uow.commit()
        self.uow.refresh(conversation)
        self.uow.refresh(user_message)
        self.uow.refresh(assistant_message)

        return (
            conversation,
            user_message,
            assistant_message,
            provider_response,
        )

    def delete_conversation(
        self,
        conversation_id: str,
        user_id: str,
    ) -> None:
        conversation = self.uow.conversations.get_for_user(
            conversation_id,
            user_id,
        )

        if not conversation:
            raise LookupError("Conversation not found")

        self.uow.conversations.delete(conversation)
        self.uow.commit()