from pydantic import BaseModel
from app.presentation.schemas.conversation_response import ConversationResponse
from app.presentation.schemas.message_response import MessageResponse
class ConversationDetailResponse(ConversationResponse):
    messages: list[MessageResponse]
