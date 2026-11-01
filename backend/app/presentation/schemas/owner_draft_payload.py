from pydantic import BaseModel, ConfigDict, Field, field_validator
from decimal import Decimal
class OwnerDraftPayload(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    email: str | None = Field(default=None, max_length=254)
    ownerRef: str | None = Field(default=None, max_length=60)
    sharePercent: Decimal | None = Field(default=None, ge=0, le=100)
    isDeceased: bool | None = None
    @field_validator("email")
    @classmethod
    def lowercase_email(cls, value: str | None) -> str | None:
        return value.strip().lower() if value else value
