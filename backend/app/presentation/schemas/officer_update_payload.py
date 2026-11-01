from pydantic import BaseModel, ConfigDict, Field
class OfficerUpdatePayload(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    fullName: str = Field(min_length=2, max_length=120)
    assignedAreaId: str | None = None
    isActive: bool
