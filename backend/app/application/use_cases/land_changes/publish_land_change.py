import logging
from app.domain.ports.i_land_change_publisher import ILandChangePublisher
from app.domain.value_objects.land_change_event import LandChangeEvent
class PublishLandChange:
    def __init__(self, publisher: ILandChangePublisher): self.publisher = publisher
    def execute(self, event: LandChangeEvent) -> None:
        try: self.publisher.publish(event)
        except Exception: logging.getLogger(__name__).exception("Land change publisher failed; committed record remains saved")
