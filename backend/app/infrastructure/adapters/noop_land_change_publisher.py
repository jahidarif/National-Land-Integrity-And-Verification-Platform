from app.domain.ports.i_land_change_publisher import ILandChangePublisher
from app.domain.value_objects.land_change_event import LandChangeEvent
class NoopLandChangePublisher(ILandChangePublisher):
    def publish(self, event: LandChangeEvent) -> None:
        return None
