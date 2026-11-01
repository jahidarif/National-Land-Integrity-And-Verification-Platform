from abc import ABC, abstractmethod
from app.domain.value_objects.land_change_event import LandChangeEvent
class ILandChangePublisher(ABC):
    @abstractmethod
    def publish(self, event: LandChangeEvent) -> None: ...
