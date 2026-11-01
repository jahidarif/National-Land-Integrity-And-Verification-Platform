from typing import Literal
from pydantic import Field
from app.presentation.schemas.land_draft_payload import LandDraftPayload
class LandUpsert(LandDraftPayload):
    recordType: Literal["RS", "BS"]
    dagNo: str = Field(min_length=1, max_length=40)
