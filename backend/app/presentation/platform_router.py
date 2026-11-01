from __future__ import annotations
import re
import uuid
from datetime import date, datetime, timezone
from decimal import Decimal
from dataclasses import asdict
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, selectinload
from app.core.config import settings
from app.core.security import require_csrf
from app.domain.models import Area, Land, LandOwner, LandTransaction, User
from app.domain.value_objects.role import Role
from app.presentation.schemas.area_payload import AreaPayload
from app.presentation.schemas.officer_create_payload import OfficerCreatePayload
from app.presentation.schemas.officer_update_payload import OfficerUpdatePayload
from app.presentation.schemas.land_draft_payload import LandDraftPayload
from app.presentation.schemas.land_upsert import LandUpsert
from app.application.support.normalize_area import NormalizeArea
from app.application.support.apply_land_upsert import ApplyLandUpsert
from app.core.value_sets import VALUE_SETS
from app.domain.value_objects.page_result import PageResult
from app.application.support.normalize_area import NormalizeArea
from app.application.support.apply_land_upsert import ApplyLandUpsert
from app.core.value_sets import VALUE_SETS
from app.domain.value_objects.page_result import PageResult
from app.infrastructure.database import get_db
from app.presentation.deps import get_current_user, require_roles
from app.domain.value_objects.land_change_event import LandChangeEvent
from app.infrastructure.adapters.noop_land_change_publisher import NoopLandChangePublisher
from app.application.use_cases.land_changes.publish_land_change import PublishLandChange

router = APIRouter(tags=["Managed land platform"])


def page_result(page: int, total: int, items: list) -> dict:
    size = settings.pagination_size
    pages = (total + size - 1) // size
    return asdict(PageResult(page=page, pageSize=size, totalCount=total, totalPages=pages,
                             hasPrevious=page > 1, hasNext=page < pages, items=items))


def area_json(area: Area) -> dict:
    return {"id": area.id, "mouza": area.mouza, "upazila": area.upazila, "district": area.district,
            "createdAt": area.created_at, "updatedAt": area.updated_at}


def officer_json(user: User) -> dict:
    return {"id": user.id, "fullName": user.full_name, "email": user.email, "isActive": user.is_active,
            "assignedAreaId": user.assigned_area_id,
            "assignedAreaName": (f"{user.assigned_area.mouza}, {user.assigned_area.upazila}, {user.assigned_area.district}" if user.assigned_area else None),
            "createdAt": user.created_at}


def land_json(land: Land) -> dict:
    result = {"landId": land.id, "areaId": land.area_id,
              "area": area_json(land.area) if land.area else None,
              "owners": [{"ownerEmail": o.owner_email, "ownerRef": o.owner_ref, "sharePercent": float(o.share_percent) if o.share_percent is not None else None, "isDeceased": o.is_deceased} for o in land.owners],
              "transactions": [{"id": t.id, "transactionId": t.transaction_id, "transactionType": t.transaction_type, "date": t.date, "amountBdt": t.amount_bdt, "deedRef": t.deed_ref, "sellerRef": t.seller_ref, "buyerRef": t.buyer_ref, "status": t.status} for t in land.transactions]}
    for column in Land.__table__.columns:
        if column.name not in {"id", "area_id", "created_at", "updated_at"}:
            value = getattr(land, column.name)
            key = re.sub(r"_([a-z])", lambda m: m.group(1).upper(), column.name)
            if isinstance(value, Decimal): value = float(value)
            result[key] = value
    result["createdAt"] = land.created_at
    result["updatedAt"] = land.updated_at
    result["hasUpdateDraft"] = bool(land.update_draft)
    return result


def normalize(value: str) -> str:
    return NormalizeArea().execute(value)


def publish_land_event(land_id: str, change_type: str, officer_id: str, updated_at: datetime) -> None:
    event = LandChangeEvent(landId=land_id, version=updated_at.isoformat(), changeType=change_type, changedBy=officer_id, changedAt=updated_at)
    PublishLandChange(NoopLandChangePublisher()).execute(event)



@router.get("/api/admin/officers")
def list_officers(page: int = 1, q: str = "", db: Session = Depends(get_db), _admin=Depends(require_roles("Admin"))):
    if page < 1: raise HTTPException(422, "page must be at least 1")
    query = select(User).options(selectinload(User.assigned_area)).where(User.role == Role.LAND_OFFICER)
    if q.strip():
        term = f"%{q.strip().lower()}%"
        query = query.where(or_(func.lower(User.full_name).like(term), func.lower(User.email).like(term)))
    total = db.scalar(select(func.count()).select_from(query.subquery())) or 0
    rows = db.scalars(query.order_by(User.created_at.desc()).offset((page-1)*settings.pagination_size).limit(settings.pagination_size)).all()
    return page_result(page, total, [officer_json(row) for row in rows])


@router.post("/api/admin/officers", status_code=201)
def create_officer(payload: OfficerCreatePayload, request: Request, db: Session = Depends(get_db), _admin=Depends(require_roles("Admin"))):
    require_csrf(request)
    email = payload.email.strip().lower()
    if db.scalar(select(User).where(User.email == email)): raise HTTPException(409, "An account with this email already exists")
    if payload.assignedAreaId and not db.get(Area, payload.assignedAreaId): raise HTTPException(404, "Area not found")
    from app.infrastructure.adapters.password_hasher import BcryptPasswordHasher
    from app.domain.models import User as UserModel
    row = UserModel(id=str(uuid.uuid4()), full_name=payload.fullName, email=email, password_hash=BcryptPasswordHasher().hash(payload.password), role=Role.LAND_OFFICER, assigned_area_id=payload.assignedAreaId, is_active=True)
    db.add(row)
    try: db.commit()
    except IntegrityError as exc: db.rollback(); raise HTTPException(409, "An account with this email already exists") from exc
    db.refresh(row)
    return officer_json(row)


@router.put("/api/admin/officers/{officer_id}")
def update_officer(officer_id: str, payload: OfficerUpdatePayload, request: Request, db: Session = Depends(get_db), _admin=Depends(require_roles("Admin"))):
    require_csrf(request)
    row = db.scalar(select(User).options(selectinload(User.assigned_area)).where(User.id == officer_id, User.role == Role.LAND_OFFICER))
    if not row: raise HTTPException(404, "Officer not found")
    if payload.assignedAreaId and not db.get(Area, payload.assignedAreaId): raise HTTPException(404, "Area not found")
    row.full_name = payload.fullName
    row.assigned_area_id = payload.assignedAreaId
    row.is_active = payload.isActive
    db.commit(); db.refresh(row)
    return officer_json(row)


@router.delete("/api/admin/officers/{officer_id}", status_code=204)
def delete_officer(officer_id: str, request: Request, db: Session = Depends(get_db), _admin=Depends(require_roles("Admin"))):
    require_csrf(request)
    row = db.scalar(select(User).where(User.id == officer_id, User.role == Role.LAND_OFFICER))
    if not row: raise HTTPException(404, "Officer not found")
    db.delete(row); db.commit()


@router.get("/api/admin/areas")
def list_areas(page: int = 1, db: Session = Depends(get_db), _admin=Depends(require_roles("Admin"))):
    if page < 1: raise HTTPException(422, "page must be at least 1")
    total = db.scalar(select(func.count()).select_from(Area)) or 0
    rows = db.scalars(select(Area).order_by(Area.district, Area.upazila, Area.mouza).offset((page-1)*settings.pagination_size).limit(settings.pagination_size)).all()
    return page_result(page, total, [area_json(row) for row in rows])


@router.get("/api/admin/areas/lookup")
def lookup_areas(q: str = "", limit: int = 20, db: Session = Depends(get_db), _admin=Depends(require_roles("Admin"))):
    limit = max(1, min(limit, 50)); query = select(Area)
    if q.strip():
        term = f"%{q.strip().lower()}%"
        query = query.where(or_(func.lower(Area.mouza).like(term), func.lower(Area.upazila).like(term), func.lower(Area.district).like(term)))
    return [{**area_json(a), "label": f"{a.mouza}, {a.upazila}, {a.district}"} for a in db.scalars(query.order_by(Area.district, Area.upazila, Area.mouza).limit(limit)).all()]


@router.post("/api/admin/areas", status_code=201)
def create_area(payload: AreaPayload, request: Request, db: Session = Depends(get_db), _admin=Depends(require_roles("Admin"))):
    require_csrf(request)
    values = {"mouza": normalize(payload.mouza), "upazila": normalize(payload.upazila), "district": normalize(payload.district)}
    existing = db.scalar(select(Area).where(func.lower(Area.mouza)==values["mouza"].lower(), func.lower(Area.upazila)==values["upazila"].lower(), func.lower(Area.district)==values["district"].lower()))
    if existing: raise HTTPException(409, "This area (mouza, upazila, district) already exists")
    row = Area(id=str(uuid.uuid4()), **values); db.add(row)
    try: db.commit()
    except IntegrityError as exc: db.rollback(); raise HTTPException(409, "This area (mouza, upazila, district) already exists") from exc
    db.refresh(row); return area_json(row)


@router.put("/api/admin/areas/{area_id}")
def update_area(area_id: str, payload: AreaPayload, request: Request, db: Session = Depends(get_db), _admin=Depends(require_roles("Admin"))):
    require_csrf(request)
    row = db.get(Area, area_id)
    if not row: raise HTTPException(404, "Area not found")
    values = {"mouza": normalize(payload.mouza), "upazila": normalize(payload.upazila), "district": normalize(payload.district)}
    duplicate = db.scalar(select(Area).where(Area.id != area_id, func.lower(Area.mouza)==values["mouza"].lower(), func.lower(Area.upazila)==values["upazila"].lower(), func.lower(Area.district)==values["district"].lower()))
    if duplicate: raise HTTPException(409, "This area (mouza, upazila, district) already exists")
    for key, value in values.items(): setattr(row, key, value)
    try: db.commit()
    except IntegrityError as exc: db.rollback(); raise HTTPException(409, "This area (mouza, upazila, district) already exists") from exc
    db.refresh(row); return area_json(row)


@router.get("/api/officer/lands")
def list_officer_lands(page: int = 1, ownerEmail: str = "", db: Session = Depends(get_db), officer=Depends(require_roles("LandOfficer"))):
    if page < 1: raise HTTPException(422, "page must be at least 1")
    if not officer.assigned_area_id: return page_result(page, 0, [])
    query = select(Land).options(selectinload(Land.area), selectinload(Land.owners), selectinload(Land.transactions)).where(Land.area_id == officer.assigned_area_id)
    if ownerEmail.strip(): query = query.join(LandOwner).where(func.lower(LandOwner.owner_email).like(f"%{ownerEmail.strip().lower()}%"))
    total = db.scalar(select(func.count()).select_from(query.subquery())) or 0
    rows = db.scalars(query.distinct().order_by(Land.id).offset((page-1)*settings.pagination_size).limit(settings.pagination_size)).all()
    return page_result(page, total, [land_json(row) for row in rows])


@router.get("/api/officer/lands/{land_id}")
def get_officer_land(land_id: str, db: Session = Depends(get_db), officer=Depends(require_roles("LandOfficer"))):
    row = db.scalar(select(Land).options(selectinload(Land.area), selectinload(Land.owners), selectinload(Land.transactions)).where(Land.id == land_id, Land.area_id == officer.assigned_area_id))
    if not row: raise HTTPException(404, "Land not found")
    return land_json(row)


@router.get("/api/user/lands")
def list_user_lands(page: int = 1, db: Session = Depends(get_db), user=Depends(require_roles("User"))):
    if page < 1: raise HTTPException(422, "page must be at least 1")
    query = select(Land).join(LandOwner).options(selectinload(Land.area), selectinload(Land.owners), selectinload(Land.transactions)).where(func.lower(LandOwner.owner_email) == user.email.lower())
    total = db.scalar(select(func.count()).select_from(query.subquery())) or 0
    rows = db.scalars(query.distinct().order_by(Land.id).offset((page-1)*settings.pagination_size).limit(settings.pagination_size)).all()
    return page_result(page, total, [land_json(row) for row in rows])


@router.get("/api/user/lands/{land_id}")
def get_user_land(land_id: str, db: Session = Depends(get_db), user=Depends(require_roles("User"))):
    row = db.scalar(select(Land).join(LandOwner).options(selectinload(Land.area), selectinload(Land.owners), selectinload(Land.transactions)).where(Land.id == land_id, func.lower(LandOwner.owner_email) == user.email.lower()))
    if not row: raise HTTPException(404, "Land not found")
    return land_json(row)


def _land_field_map() -> dict[str, str]:
    return {re.sub(r"_([a-z])", lambda m: m.group(1).upper(), c.name): c.name for c in Land.__table__.columns}



@router.post("/api/officer/lands", status_code=201)
def create_officer_land(payload: LandUpsert, request: Request, db: Session = Depends(get_db), officer=Depends(require_roles("LandOfficer"))):
    require_csrf(request)
    if not officer.assigned_area_id: raise HTTPException(403, "You must be assigned to an area before creating land records")
    payload = payload.model_dump(exclude_unset=True, mode="json")
    if len(str(payload).encode()) > 65536: raise HTTPException(413, "Land payload exceeds 64 KB")
    record_type, dag_no = payload["recordType"], payload["dagNo"]
    area = db.get(Area, officer.assigned_area_id)
    land_id = f"LAND-BD-{re.sub('[^A-Z0-9]+', '-', area.district.upper()).strip('-')}-{uuid.uuid4().hex[:8].upper()}"
    row = Land(id=land_id, area_id=officer.assigned_area_id, record_type=record_type, dag_no=str(dag_no))
    try:
        ApplyLandUpsert().execute(row, payload, officer, True, lambda email: db.scalar(select(User).where(User.email == email)))
        db.add(row); db.commit(); db.refresh(row); publish_land_event(row.id, "created", officer.id, row.updated_at)
    except ValueError as exc:
        db.rollback(); raise HTTPException(422, str(exc)) from exc
    except IntegrityError as exc:
        db.rollback(); raise HTTPException(409, "A land with this record type and Dag number already exists in this area") from exc
    return land_json(db.scalar(select(Land).options(selectinload(Land.area), selectinload(Land.owners), selectinload(Land.transactions)).where(Land.id == row.id)))


@router.put("/api/officer/lands/{land_id}")
def update_officer_land(land_id: str, payload: LandUpsert, request: Request, db: Session = Depends(get_db), officer=Depends(require_roles("LandOfficer"))):
    require_csrf(request)
    if not officer.assigned_area_id: raise HTTPException(403, "You must be assigned to an area before editing land records")
    row = db.scalar(select(Land).options(selectinload(Land.area), selectinload(Land.owners), selectinload(Land.transactions)).where(Land.id == land_id, Land.area_id == officer.assigned_area_id))
    if not row: raise HTTPException(404, "Land not found")
    payload = payload.model_dump(exclude_unset=True, mode="json")
    if len(str(payload).encode()) > 65536: raise HTTPException(413, "Land payload exceeds 64 KB")
    try:
        ApplyLandUpsert().execute(row, payload, officer, False, lambda email: db.scalar(select(User).where(User.email == email))); db.commit(); db.refresh(row); publish_land_event(row.id, "updated", officer.id, row.updated_at)
    except ValueError as exc:
        db.rollback(); raise HTTPException(422, str(exc)) from exc
    except IntegrityError as exc:
        db.rollback(); raise HTTPException(409, "A land with this record type and Dag number already exists in this area") from exc
    return land_json(row)


@router.get("/api/officer/drafts/summary")
def draft_summary(db: Session = Depends(get_db), officer=Depends(require_roles("LandOfficer"))):
    from app.domain.models import LandCreateDraft, LandUpdateDraft
    if not officer.assigned_area_id: return {"updates": 0, "creates": 0}
    updates = db.scalar(select(func.count()).select_from(LandUpdateDraft).join(Land).where(Land.area_id == officer.assigned_area_id)) or 0
    creates = db.scalar(select(func.count()).select_from(LandCreateDraft).where(LandCreateDraft.area_id == officer.assigned_area_id)) or 0
    return {"updates": updates, "creates": creates}


@router.get("/api/officer/drafts/updates")
def list_update_drafts(page: int = 1, db: Session = Depends(get_db), officer=Depends(require_roles("LandOfficer"))):
    from app.domain.models import LandUpdateDraft
    if not officer.assigned_area_id: return page_result(page, 0, [])
    query = select(LandUpdateDraft).join(Land).where(Land.area_id == officer.assigned_area_id)
    total = db.scalar(select(func.count()).select_from(query.subquery())) or 0
    rows = db.scalars(query.order_by(LandUpdateDraft.updated_at.desc()).offset((page-1)*settings.pagination_size).limit(settings.pagination_size)).all()
    return page_result(page, total, [{"landId": r.land_id, "payload": r.payload, "baseUpdatedAt": r.base_updated_at, "updatedAt": r.updated_at, "isStale": r.land.updated_at != r.base_updated_at} for r in rows])


@router.get("/api/officer/drafts/updates/{land_id}")
def get_update_draft(land_id: str, db: Session = Depends(get_db), officer=Depends(require_roles("LandOfficer"))):
    from app.domain.models import LandUpdateDraft
    row = db.scalar(select(LandUpdateDraft).join(Land).where(LandUpdateDraft.land_id == land_id, Land.area_id == officer.assigned_area_id))
    if not row: raise HTTPException(404, "Draft not found")
    return {"landId": row.land_id, "payload": row.payload, "baseUpdatedAt": row.base_updated_at, "isStale": row.land.updated_at != row.base_updated_at}


@router.put("/api/officer/drafts/updates/{land_id}")
def save_update_draft(land_id: str, payload: LandDraftPayload, request: Request, db: Session = Depends(get_db), officer=Depends(require_roles("LandOfficer"))):
    from app.domain.models import LandUpdateDraft
    require_csrf(request)
    payload_data = payload.model_dump(exclude_unset=True, mode="json")
    if len(str(payload_data).encode()) > 65536: raise HTTPException(413, "Draft payload exceeds 64 KB")
    land = db.scalar(select(Land).where(Land.id == land_id, Land.area_id == officer.assigned_area_id))
    if not land: raise HTTPException(404, "Land not found")
    row = db.get(LandUpdateDraft, land_id)
    if row is None: row = LandUpdateDraft(land_id=land_id, payload=payload_data, base_updated_at=land.updated_at, created_by=officer.id, updated_by=officer.id); db.add(row)
    else: row.payload = payload_data; row.updated_by = officer.id
    db.commit(); db.refresh(row)
    return {"landId": row.land_id, "payload": row.payload, "baseUpdatedAt": row.base_updated_at, "isStale": row.base_updated_at != land.updated_at}


@router.delete("/api/officer/drafts/updates/{land_id}", status_code=204)
def delete_update_draft(land_id: str, request: Request, db: Session = Depends(get_db), officer=Depends(require_roles("LandOfficer"))):
    from app.domain.models import LandUpdateDraft
    require_csrf(request)
    row = db.scalar(select(LandUpdateDraft).join(Land).where(LandUpdateDraft.land_id == land_id, Land.area_id == officer.assigned_area_id))
    if not row: raise HTTPException(404, "Draft not found")
    db.delete(row); db.commit()


@router.post("/api/officer/drafts/updates/{land_id}/publish")
def publish_update_draft(land_id: str, request: Request, db: Session = Depends(get_db), officer=Depends(require_roles("LandOfficer"))):
    from app.domain.models import LandUpdateDraft
    require_csrf(request)
    row = db.scalar(select(LandUpdateDraft).join(Land).options(selectinload(LandUpdateDraft.land).selectinload(Land.area), selectinload(LandUpdateDraft.land).selectinload(Land.owners), selectinload(LandUpdateDraft.land).selectinload(Land.transactions)).where(LandUpdateDraft.land_id == land_id, Land.area_id == officer.assigned_area_id))
    if not row: raise HTTPException(404, "Draft not found")
    if row.base_updated_at != row.land.updated_at: raise HTTPException(409, "This draft is stale because the land record changed after the draft was started")
    try:
        strict_payload = LandUpsert.model_validate(row.payload).model_dump(exclude_unset=True, mode="json")
        ApplyLandUpsert().execute(row.land, strict_payload, officer, False, lambda email: db.scalar(select(User).where(User.email == email)))
        db.delete(row); db.commit(); publish_land_event(land_id, "updated", officer.id, row.land.updated_at)
    except ValueError as exc: db.rollback(); raise HTTPException(422, str(exc)) from exc
    except IntegrityError as exc: db.rollback(); raise HTTPException(409, "Could not publish this land draft") from exc
    return {"landId": land_id, "published": True}


@router.get("/api/officer/drafts/creates")
def list_create_drafts(page: int = 1, db: Session = Depends(get_db), officer=Depends(require_roles("LandOfficer"))):
    from app.domain.models import LandCreateDraft
    query = select(LandCreateDraft).where(LandCreateDraft.area_id == officer.assigned_area_id) if officer.assigned_area_id else select(LandCreateDraft).where(False)
    total = db.scalar(select(func.count()).select_from(query.subquery())) or 0
    rows = db.scalars(query.order_by(LandCreateDraft.updated_at.desc()).offset((page-1)*settings.pagination_size).limit(settings.pagination_size)).all()
    return page_result(page, total, [{"id": r.id, "payload": r.payload, "updatedAt": r.updated_at} for r in rows])


@router.post("/api/officer/drafts/creates", status_code=201)
def create_create_draft(payload: LandDraftPayload, request: Request, db: Session = Depends(get_db), officer=Depends(require_roles("LandOfficer"))):
    from app.domain.models import LandCreateDraft
    require_csrf(request)
    if not officer.assigned_area_id: raise HTTPException(403, "You must be assigned to an area before creating land records")
    payload_data = payload.model_dump(exclude_unset=True, mode="json")
    if len(str(payload_data).encode()) > 65536: raise HTTPException(413, "Draft payload exceeds 64 KB")
    row = LandCreateDraft(id=str(uuid.uuid4()), area_id=officer.assigned_area_id, payload=payload_data, created_by=officer.id, updated_by=officer.id)
    db.add(row); db.commit(); db.refresh(row)
    return {"id": row.id, "payload": row.payload, "updatedAt": row.updated_at}


@router.get("/api/officer/drafts/creates/{draft_id}")
def get_create_draft(draft_id: str, db: Session = Depends(get_db), officer=Depends(require_roles("LandOfficer"))):
    from app.domain.models import LandCreateDraft
    row = db.scalar(select(LandCreateDraft).where(LandCreateDraft.id == draft_id, LandCreateDraft.area_id == officer.assigned_area_id))
    if not row: raise HTTPException(404, "Draft not found")
    return {"id": row.id, "payload": row.payload, "updatedAt": row.updated_at}


@router.put("/api/officer/drafts/creates/{draft_id}")
def save_create_draft(draft_id: str, payload: LandDraftPayload, request: Request, db: Session = Depends(get_db), officer=Depends(require_roles("LandOfficer"))):
    from app.domain.models import LandCreateDraft
    require_csrf(request)
    payload_data = payload.model_dump(exclude_unset=True, mode="json")
    if len(str(payload_data).encode()) > 65536: raise HTTPException(413, "Draft payload exceeds 64 KB")
    row = db.scalar(select(LandCreateDraft).where(LandCreateDraft.id == draft_id, LandCreateDraft.area_id == officer.assigned_area_id))
    if not row: raise HTTPException(404, "Draft not found")
    row.payload = payload_data; row.updated_by = officer.id; db.commit(); db.refresh(row)
    return {"id": row.id, "payload": row.payload, "updatedAt": row.updated_at}


@router.delete("/api/officer/drafts/creates/{draft_id}", status_code=204)
def delete_create_draft(draft_id: str, request: Request, db: Session = Depends(get_db), officer=Depends(require_roles("LandOfficer"))):
    from app.domain.models import LandCreateDraft
    require_csrf(request)
    row = db.scalar(select(LandCreateDraft).where(LandCreateDraft.id == draft_id, LandCreateDraft.area_id == officer.assigned_area_id))
    if not row: raise HTTPException(404, "Draft not found")
    db.delete(row); db.commit()


@router.post("/api/officer/drafts/creates/{draft_id}/publish", status_code=201)
def publish_create_draft(draft_id: str, request: Request, db: Session = Depends(get_db), officer=Depends(require_roles("LandOfficer"))):
    from app.domain.models import LandCreateDraft
    require_csrf(request)
    row = db.scalar(select(LandCreateDraft).where(LandCreateDraft.id == draft_id, LandCreateDraft.area_id == officer.assigned_area_id))
    if not row: raise HTTPException(404, "Draft not found")
    try:
        payload = LandUpsert.model_validate(row.payload).model_dump(exclude_unset=True, mode="json")
    except Exception as exc:
        raise HTTPException(422, "The land draft is incomplete or invalid and cannot be published") from exc
    area = db.get(Area, row.area_id)
    land_id = f"LAND-BD-{re.sub('[^A-Z0-9]+', '-', area.district.upper()).strip('-')}-{uuid.uuid4().hex[:8].upper()}"
    land = Land(id=land_id, area_id=row.area_id, record_type=payload["recordType"], dag_no=str(payload["dagNo"]))
    try: ApplyLandUpsert().execute(land, payload, officer, True, lambda email: db.scalar(select(User).where(User.email == email))); db.add(land); db.delete(row); db.commit(); publish_land_event(land_id, "created", officer.id, land.updated_at)
    except ValueError as exc: db.rollback(); raise HTTPException(422, str(exc)) from exc
    except IntegrityError as exc: db.rollback(); raise HTTPException(409, "A land with this record type and Dag number already exists in this area") from exc
    return {"landId": land_id, "published": True}
