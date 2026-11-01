import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from app.domain.base import Base
from app.domain.models import User, Role
from app.domain.errors.conflict_error import ConflictError
from app.infrastructure.unit_of_work import SqlAlchemyUnitOfWork


def test_role_is_immutable_after_insert():
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        user = User(id="role-user", full_name="Officer", email="officer@demo.local", password_hash="hash", role=Role.LAND_OFFICER)
        db.add(user); db.flush()
        with pytest.raises(ValueError, match="cannot be changed"):
            user.role = Role.USER
    engine.dispose()


def test_unit_of_work_maps_integrity_error_to_conflict():
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        db.add(User(id="one", full_name="One", email="same@demo.local", password_hash="hash", role=Role.USER))
        db.commit()
        db.add(User(id="two", full_name="Two", email="same@demo.local", password_hash="hash", role=Role.USER))
        with pytest.raises(ConflictError):
            SqlAlchemyUnitOfWork(db).commit()
    engine.dispose()


def test_officer_update_dto_rejects_role_field():
    from pydantic import ValidationError
    from app.presentation.schemas.officer_update_payload import OfficerUpdatePayload
    with pytest.raises(ValidationError):
        OfficerUpdatePayload.model_validate({"fullName":"Officer","assignedAreaId":None,"isActive":True,"role":"Admin"})


def test_land_change_publisher_exception_does_not_escape():
    from datetime import datetime, timezone
    from app.application.use_cases.land_changes.publish_land_change import PublishLandChange
    from app.domain.value_objects.land_change_event import LandChangeEvent
    class FailingPublisher:
        def publish(self, event):
            raise RuntimeError("future sync is unavailable")
    event = LandChangeEvent(landId="LAND-BD-DEMO-0001", version="v1", changeType="updated", changedBy="officer", changedAt=datetime.now(timezone.utc))
    PublishLandChange(FailingPublisher()).execute(event)
