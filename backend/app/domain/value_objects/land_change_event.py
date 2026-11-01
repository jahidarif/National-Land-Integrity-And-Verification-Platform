from dataclasses import dataclass
from datetime import datetime
@dataclass(frozen=True)
class LandChangeEvent:
    landId: str
    version: str
    changeType: str
    changedBy: str
    changedAt: datetime
