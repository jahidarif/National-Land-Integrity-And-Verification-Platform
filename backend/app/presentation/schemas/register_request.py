from pydantic import BaseModel, EmailStr, Field, field_validator
class RegisterRequest(BaseModel):
    full_name: str = Field(min_length=2, max_length=120)
    role: str = Field(default="User", pattern="^(User|LandOfficer)$")
    email: EmailStr
    password: str = Field(min_length=8, max_length=72)
    @field_validator("full_name")
    @classmethod
    def name_not_blank(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned: raise ValueError("Name cannot be blank")
        return cleaned
