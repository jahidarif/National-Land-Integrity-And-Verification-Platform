from pydantic import BaseModel, ConfigDict, Field
class AreaPayload(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    mouza: str = Field(min_length=1, max_length=120)
    upazila: str = Field(min_length=1, max_length=120)
    district: str = Field(min_length=1, max_length=120)
