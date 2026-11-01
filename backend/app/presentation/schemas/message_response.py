from datetime import datetime
from pydantic import BaseModel, ConfigDict
class MessageResponse(BaseModel):
    id: str
    conversation_id: str
    role: str
    content: str
    sequence_no: int
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)
