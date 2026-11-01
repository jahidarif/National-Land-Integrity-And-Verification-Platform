from __future__ import annotations
import hashlib, logging, re, uuid
from pathlib import Path
from fastapi import APIRouter, Depends, File, HTTPException, Request, UploadFile
from sqlalchemy import func, select
from sqlalchemy.orm import Session
from app.core.config import settings
from app.core.security import require_csrf
from app.domain.models import Document
from app.infrastructure.database import get_db
from app.infrastructure.adapters.s3.s3_document_uploader import S3DocumentUploader
from app.infrastructure.adapters.s3.s3_document_deleter import S3DocumentDeleter
from app.infrastructure.adapters.s3.s3_document_url_signer import S3DocumentUrlSigner
from app.application.support.attachment_validator import AttachmentValidator
from app.presentation.deps import require_roles
logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/user/documents", tags=["User documents"])

def _safe_name(filename: str) -> str:
    name = Path(filename or "document").name
    name = re.sub(r"[^A-Za-z0-9._ -]", "_", name).strip(" .")[:255]
    return name or "document"

def _page(page: int, total: int, items: list) -> dict:
    size = settings.pagination_size; pages = (total + size - 1) // size
    return {"page": page, "pageSize": size, "totalCount": total, "totalPages": pages, "hasPrevious": page > 1, "hasNext": page < pages, "items": items}

def _json(row: Document) -> dict:
    return {"id": row.id, "fileName": row.original_filename, "contentType": row.content_type, "sizeBytes": row.size_bytes, "createdAt": row.created_at}

@router.get("")
def list_documents(page: int = 1, q: str = "", db: Session = Depends(get_db), user=Depends(require_roles("User"))):
    if page < 1: raise HTTPException(422, "page must be at least 1")
    query = select(Document).where(Document.user_id == user.id)
    if q.strip(): query = query.where(func.lower(Document.original_filename).like(f"%{q.strip().lower()}%"))
    total = db.scalar(select(func.count()).select_from(query.subquery())) or 0
    rows = db.scalars(query.order_by(Document.created_at.desc()).offset((page-1)*settings.pagination_size).limit(settings.pagination_size)).all()
    return _page(page, total, [_json(r) for r in rows])

@router.post("", status_code=201)
async def upload_document(request: Request, file: UploadFile = File(...), db: Session = Depends(get_db), user=Depends(require_roles("User"))):
    require_csrf(request)
    count = db.scalar(select(func.count()).select_from(Document).where(Document.user_id == user.id)) or 0
    if count >= settings.documents_max_per_user: raise HTTPException(409, "You have reached the document storage limit")
    raw = await file.read()
    try: content_type = AttachmentValidator().execute(file.filename or "document", file.content_type or "application/octet-stream", raw, settings.max_upload_mb)
    except ValueError as exc: raise HTTPException(422, str(exc)) from exc
    filename = _safe_name(file.filename or "document"); document_id = str(uuid.uuid4())
    key = f"users/{user.id}/documents/{document_id}/{filename}"
    deleter = None
    uploaded = False
    try:
        uploader = S3DocumentUploader(); deleter = S3DocumentDeleter()
        uploader.upload(key, raw, content_type)
        uploaded = True
        row = Document(id=document_id, user_id=user.id, original_filename=filename, content_type=content_type, size_bytes=len(raw), storage_key=key, checksum_sha256=hashlib.sha256(raw).hexdigest())
        db.add(row); db.commit(); db.refresh(row); return _json(row)
    except Exception as exc:
        db.rollback()
        if uploaded and deleter is not None:
            try: deleter.delete(key)
            except Exception: logger.exception("Failed to compensate S3 upload %s", key)
        logger.exception("Document upload failed")
        raise HTTPException(502, "Could not store the document") from exc

@router.get("/{document_id}/url")
def get_document_url(document_id: str, db: Session = Depends(get_db), user=Depends(require_roles("User"))):
    row = db.scalar(select(Document).where(Document.id == document_id, Document.user_id == user.id))
    if not row: raise HTTPException(404, "Document not found")
    try: url = S3DocumentUrlSigner().sign(row.storage_key, row.original_filename, row.content_type)
    except Exception as exc: logger.exception("Could not sign document URL"); raise HTTPException(502, "Could not create document URL") from exc
    return {"url": url, "expiresInSeconds": settings.s3_presign_expires_seconds}

@router.delete("/{document_id}", status_code=204)
def delete_document(document_id: str, request: Request, db: Session = Depends(get_db), user=Depends(require_roles("User"))):
    require_csrf(request)
    row = db.scalar(select(Document).where(Document.id == document_id, Document.user_id == user.id))
    if not row: raise HTTPException(404, "Document not found")
    key = row.storage_key; db.delete(row); db.commit()
    try: S3DocumentDeleter().delete(key)
    except Exception: logger.exception("S3 object deletion failed after document row deletion: %s", key)
