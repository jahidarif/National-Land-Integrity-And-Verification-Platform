from sqlalchemy import func, select
from sqlalchemy.orm import Session, joinedload
from app.domain.entities import Conversation, Message, RefreshToken, User

class SqlAlchemyUserRepository:
    def __init__(self, db: Session): self.db = db
    def get_by_id(self, user_id: str): return self.db.scalar(select(User).where(User.id == user_id))
    def get_by_email(self, email: str): return self.db.scalar(select(User).where(User.email == email))
    def add(self, user: User) -> None: self.db.add(user)

class SqlAlchemyConversationRepository:
    def __init__(self, db: Session): self.db = db
    def get_for_user(self, conversation_id: str, user_id: str):
        return self.db.scalar(select(Conversation).where(Conversation.id == conversation_id, Conversation.user_id == user_id))
    def list_for_user(self, user_id: str, limit: int = 100):
        return list(self.db.scalars(select(Conversation).where(Conversation.user_id == user_id).order_by(Conversation.updated_at.desc()).limit(limit)).all())
    def add(self, conversation: Conversation) -> None: self.db.add(conversation)
    def delete(self, conversation: Conversation) -> None: self.db.delete(conversation)

class SqlAlchemyMessageRepository:
    def __init__(self, db: Session): self.db = db
    def list_for_conversation(self, conversation_id: str):
        return list(self.db.scalars(select(Message).where(Message.conversation_id == conversation_id).order_by(Message.sequence_no.asc())).all())
    def add(self, message: Message) -> None: self.db.add(message)
    def count_for_conversation(self, conversation_id: str) -> int:
        return int(self.db.scalar(select(func.count()).select_from(Message).where(Message.conversation_id == conversation_id)) or 0)

class SqlAlchemyRefreshTokenRepository:
    def __init__(self, db: Session): self.db = db
    def get_by_jti(self, jti: str): return self.db.scalar(select(RefreshToken).where(RefreshToken.jti == jti))
    def add(self, token: RefreshToken) -> None: self.db.add(token)
