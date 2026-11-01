from datetime import datetime
from pydantic import BaseModel, ConfigDict
class ConversationResponse(BaseModel):
    id: str
    title: str
    created_at: datetime
    updated_at: datetime
    model_config = ConfigDict(from_attributes=True)
