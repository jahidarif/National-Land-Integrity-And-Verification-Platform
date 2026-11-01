from pydantic import BaseModel, Field, field_validator
class MessageCreate(BaseModel):
    query: str = Field(min_length=1, max_length=8000)
    @field_validator("query")
    @classmethod
    def clean_query(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned: raise ValueError("Message cannot be blank")
        return cleaned
    model_config = {"extra": "forbid"}
