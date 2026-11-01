"""Compatibility exports for Project A's existing chat/auth adapters."""
from app.domain.base import Base
from app.domain.timestamped import Timestamped
from datetime import datetime, timezone
def utcnow(): return datetime.now(timezone.utc)
from app.domain.models import Conversation, Message, RefreshToken, User, Role

__all__ = ["Base", "Timestamped", "utcnow", "Conversation", "Message", "RefreshToken", "User", "Role"]
