from pydantic import BaseModel, ConfigDict, Field, EmailStr
class OfficerCreatePayload(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    fullName: str = Field(min_length=2, max_length=120)
    email: EmailStr
    password: str = Field(min_length=8, max_length=72)
    assignedAreaId: str | None = None
