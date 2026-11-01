from app.domain.entities import Conversation, Message, User
from sqlalchemy import select
from sqlalchemy.orm import object_session
from app.domain.models import LandOwner

def user_response(entity: User) -> dict:
    session = object_session(entity)
    owned_land_ids = session.scalars(select(LandOwner.land_id).where(LandOwner.owner_email == entity.email.lower())).all() if session else []
    return {"id": entity.id, "fullName": entity.full_name, "email": entity.email, "role": entity.role.value if hasattr(entity.role, "value") else entity.role, "isActive": entity.is_active, "assignedAreaId": entity.assigned_area_id, "assignedAreaName": (f"{entity.assigned_area.mouza}, {entity.assigned_area.upazila}, {entity.assigned_area.district}" if entity.assigned_area else None), "ownedLandIds": list(owned_land_ids)}

def conversation_response(entity: Conversation) -> dict:
    return {"id": entity.id, "title": entity.title, "created_at": entity.created_at, "updated_at": entity.updated_at}

def message_response(entity: Message) -> dict:
    return {"id": entity.id, "conversation_id": entity.conversation_id, "role": entity.role, "content": entity.content, "sequence_no": entity.sequence_no, "created_at": entity.created_at}
