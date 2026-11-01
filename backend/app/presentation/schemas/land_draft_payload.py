from datetime import date, datetime
from decimal import Decimal
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field, field_validator
from app.presentation.schemas.owner_draft_payload import OwnerDraftPayload
from app.presentation.schemas.transaction_draft_payload import TransactionDraftPayload
class LandDraftPayload(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    recordType: Literal["RS", "BS"] | None = None
    dagNo: str | None = Field(default=None, max_length=40)
    jlNo: str | None = Field(default=None, max_length=40)
    khatianNo: str | None = Field(default=None, max_length=40)
    areaDecimal: Decimal | None = Field(default=None, ge=0, le=9999999999)
    landClass: str | None = Field(default=None, max_length=40)
    khatianRef: str | None = Field(default=None, max_length=60)
    khatianStatus: str | None = Field(default=None, max_length=40)
    deedNo: str | None = Field(default=None, max_length=60)
    deedDate: date | None = None
    deedRegistrationOffice: str | None = Field(default=None, max_length=160)
    mutationRef: str | None = Field(default=None, max_length=60)
    mutationStatus: str | None = Field(default=None, max_length=40)
    dcrRef: str | None = Field(default=None, max_length=60)
    dcrStatus: str | None = Field(default=None, max_length=40)
    dakhilaRef: str | None = Field(default=None, max_length=60)
    dakhilaStatus: str | None = Field(default=None, max_length=40)
    ownershipStatus: str | None = Field(default=None, max_length=40)
    deathIndicator: str | None = Field(default=None, max_length=10)
    successorProcess: str | None = Field(default=None, max_length=40)
    mutationAfterSuccession: str | None = Field(default=None, max_length=40)
    successionStatus: str | None = Field(default=None, max_length=40)
    caseExists: bool | None = None
    caseRef: str | None = Field(default=None, max_length=60)
    caseType: str | None = Field(default=None, max_length=60)
    caseStatus: str | None = Field(default=None, max_length=40)
    mortgageExists: bool | None = None
    mortgageRef: str | None = Field(default=None, max_length=60)
    mortgageStatus: str | None = Field(default=None, max_length=40)
    lastSoldPriceBdt: int | None = Field(default=None, ge=0)
    lastSoldDate: date | None = None
    lastSoldDeedRef: str | None = Field(default=None, max_length=60)
    reservedPriceBdt: int | None = Field(default=None, ge=0)
    reservedPriceDate: date | None = None
    priceFlag: str | None = Field(default=None, max_length=40)
    overallStatus: str | None = Field(default=None, max_length=60)
    riskLevel: str | None = Field(default=None, max_length=10)
    verificationFlags: str | None = Field(default=None, max_length=400)
    documentLevelStatus: str | None = Field(default=None, max_length=40)
    ownershipCheck: str | None = Field(default=None, max_length=40)
    successionCheck: str | None = Field(default=None, max_length=40)
    caseCheck: str | None = Field(default=None, max_length=40)
    mortgageCheck: str | None = Field(default=None, max_length=40)
    priceCheck: str | None = Field(default=None, max_length=40)
    verifiedAt: datetime | None = None
    verificationVersion: str | None = Field(default=None, max_length=60)
    sourceSnapshotVersion: str | None = Field(default=None, max_length=60)
    owners: list[OwnerDraftPayload] | None = None
    transactions: list[TransactionDraftPayload] | None = None

    @field_validator("deedDate", "lastSoldDate", "reservedPriceDate", "verifiedAt", mode="before")
    @classmethod
    def blank_dates_to_none(cls, value):
        return None if value == "" else value

    @field_validator("areaDecimal", "lastSoldPriceBdt", "reservedPriceBdt", mode="before")
    @classmethod
    def blank_numbers_to_none(cls, value):
        return None if value == "" else value
