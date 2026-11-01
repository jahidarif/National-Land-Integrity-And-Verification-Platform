from datetime import date as DateType
from pydantic import BaseModel, ConfigDict, Field, field_validator
class TransactionDraftPayload(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    id: str | None = Field(default=None, max_length=36)
    transactionId: str | None = Field(default=None, max_length=40)
    transactionType: str | None = Field(default=None, max_length=30)
    date: DateType | None = None
    amountBdt: int | None = Field(default=None, ge=0)
    deedRef: str | None = Field(default=None, max_length=60)
    sellerRef: str | None = Field(default=None, max_length=60)
    buyerRef: str | None = Field(default=None, max_length=60)
    status: str | None = Field(default=None, max_length=40)

    @field_validator("date", mode="before")
    @classmethod
    def blank_date_to_none(cls, value):
        return None if value == "" else value

    @field_validator("amountBdt", mode="before")
    @classmethod
    def blank_amount_to_none(cls, value):
        return None if value == "" else value
