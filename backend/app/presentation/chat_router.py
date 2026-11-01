from __future__ import annotations

import asyncio
import json
import logging
import shutil
import subprocess
import tempfile
import time
import uuid
from pathlib import Path
from typing import Any
from urllib.parse import quote

import httpx
from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    Header,
    HTTPException,
    Request,
    UploadFile,
)
from fastapi.responses import JSONResponse, Response
from starlette.concurrency import run_in_threadpool

from app.core.config import settings
from app.core.security import require_csrf
from app.domain.entities import User
from app.domain.models import Document, Role
from app.infrastructure.database import get_db
from app.infrastructure.adapters.s3.s3_document_reader import S3DocumentReader
from app.application.support.attachment_validator import AttachmentValidator
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.presentation.deps import get_chat_service, get_current_user, require_roles
from app.presentation.schemas import (
    ConversationDetailResponse,
    ConversationResponse,
    MessageCreate,
)
from app.presentation.serializers import (
    conversation_response,
    message_response,
)

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/v1/chat",
    tags=["Chat"],
)

CHORUS_SPEECHES_URL = (
    "https://api.maira.gigalogy.com/chorus/v1/speeches"
)

# Small process-local TTL cache.
# The database remains the source of truth.
_cache: dict[str, tuple[float, object]] = {}


def cache_get(key):
    item = _cache.get(key)

    if not item:
        return None

    if item[0] < time.monotonic():
        _cache.pop(key, None)
        return None

    return item[1]


def cache_set(key, value):
    _cache[key] = (
        time.monotonic() + settings.chat_cache_ttl_seconds,
        value,
    )


def invalidate_user(user_id):
    for key in list(_cache):
        if (
            key.startswith(f"conversations:{user_id}:")
            or key.startswith(f"conversation:{user_id}:")
        ):
            _cache.pop(key, None)


@router.get(
    "/conversations",
    response_model=list[ConversationResponse],
)
def list_conversations(
    user: User = Depends(require_roles("LandOfficer", "User")),
    service: Any = Depends(get_chat_service),
):
    key = f"conversations:{user.id}:list"
    cached = cache_get(key)

    if cached is not None:
        return cached

    result = [
        conversation_response(row)
        for row in service.list_conversations(user.id)
    ]

    cache_set(key, result)
    return result


@router.get(
    "/conversations/{conversation_id}",
    response_model=ConversationDetailResponse,
)
def get_conversation(
    conversation_id: str,
    user: User = Depends(require_roles("LandOfficer", "User")),
    service: Any = Depends(get_chat_service),
):
    key = f"conversation:{user.id}:{conversation_id}"
    cached = cache_get(key)

    if cached is not None:
        return cached

    try:
        conversation, messages = service.get_conversation(
            conversation_id,
            user.id,
        )
    except LookupError as exc:
        raise HTTPException(
            status_code=404,
            detail=str(exc),
        ) from exc

    result = {
        **conversation_response(conversation),
        "messages": [
            message_response(row)
            for row in messages
        ],
    }

    cache_set(key, result)
    return result


def original_response(
    response,
    conversation_id: str | None = None,
):
    headers = (
        {"X-Conversation-ID": conversation_id}
        if conversation_id
        else {}
    )

    if isinstance(response, httpx.Response):
        return Response(
            content=response.content,
            status_code=response.status_code,
            media_type=response.headers.get(
                "content-type",
                "application/json",
            ),
            headers=headers,
        )

    return JSONResponse(
        content=response,
        headers=headers,
    )


@router.post("/messages")
def send_message(
    data: MessageCreate,
    request: Request,
    conversation_id: str | None = Header(
        None,
        alias="X-Conversation-ID",
    ),
    user: User = Depends(require_roles("LandOfficer", "User")),
    service: Any = Depends(get_chat_service),
):
    require_csrf(request)

    try:
        conversation, _, _, response = service.send_message(
            user.id,
            data.query,
            conversation_id,
        )
    except httpx.HTTPStatusError as exc:
        return original_response(exc.response)
    except httpx.TimeoutException as exc:
        raise HTTPException(
            status_code=504,
            detail="Maira request timed out",
        ) from exc
    except httpx.RequestError as exc:
        raise HTTPException(
            status_code=502,
            detail="Could not connect to Maira",
        ) from exc
    except LookupError as exc:
        raise HTTPException(
            status_code=404,
            detail=str(exc),
        ) from exc
    except ValueError as exc:
        raise HTTPException(
            status_code=422,
            detail=str(exc),
        ) from exc
    except Exception as exc:
        logger.exception("Assistant request failed")

        raise HTTPException(
            status_code=502,
            detail="Assistant request failed. Check backend logs.",
        ) from exc

    invalidate_user(user.id)

    return original_response(
        response,
        conversation.id,
    )


@router.post("/messages-with-files")
async def send_message_with_files(
    request: Request,
    query: str = Form(""),
    conversation_id: str | None = Header(
        None,
        alias="X-Conversation-ID",
    ),
    files: list[UploadFile] = File(default=[]),
    document_ids: list[str] = Form(default=[]),
    user: User = Depends(require_roles("LandOfficer", "User")),
    service: Any = Depends(get_chat_service),
    db: Session = Depends(get_db),
):
    require_csrf(request)

    if not query.strip() and not files and not document_ids:
        raise HTTPException(
            status_code=422,
            detail="Write a message or attach a file",
        )

    if document_ids and user.role != Role.USER:
        raise HTTPException(status_code=403, detail="Only Users can attach stored documents")

    if len(files) + len(document_ids) > 5:
        raise HTTPException(
            status_code=422,
            detail="Attach at most 5 files",
        )

    upload_root = Path(settings.upload_dir)
    upload_root.mkdir(
        parents=True,
        exist_ok=True,
    )

    saved = []

    try:
        for uploaded_file in files:
            suffix = Path(
                uploaded_file.filename or "upload.bin"
            ).suffix.lower()

            allowed = {
                ".pdf",
                ".png",
                ".jpg",
                ".jpeg",
                ".txt",
                ".csv",
            }

            if suffix not in allowed:
                raise HTTPException(
                    status_code=415,
                    detail=f"Unsupported file type: {suffix}",
                )

            raw = await uploaded_file.read()
            limit = settings.max_upload_mb * 1024 * 1024

            if len(raw) > limit:
                raise HTTPException(
                    status_code=413,
                    detail=(
                        f"Each file must be "
                        f"{settings.max_upload_mb} MB or smaller"
                    ),
                )

            try:
                AttachmentValidator().execute(uploaded_file.filename or suffix, uploaded_file.content_type or "application/octet-stream", raw, settings.max_upload_mb)
            except ValueError as exc:
                raise HTTPException(status_code=422, detail=str(exc)) from exc
            stored = f"{uuid.uuid4().hex}{suffix}"
            path = upload_root / stored
            path.write_bytes(raw)
            saved.append(
                {
                    "filename": Path(uploaded_file.filename or stored).name,
                    "path": str(path),
                    "stored_name": stored,
                }
            )

        if document_ids:
            documents = db.scalars(select(Document).where(Document.id.in_(document_ids), Document.user_id == user.id)).all()
            if len(documents) != len(set(document_ids)):
                raise HTTPException(status_code=404, detail="One or more selected documents were not found")
            reader = S3DocumentReader()
            for document in documents:
                raw = reader.read(document.storage_key)
                try:
                    AttachmentValidator().execute(document.original_filename, document.content_type, raw, settings.max_upload_mb)
                except ValueError as exc:
                    raise HTTPException(status_code=422, detail=str(exc)) from exc
                stored = f"{uuid.uuid4().hex}{Path(document.original_filename).suffix.lower()}"
                path = upload_root / stored
                path.write_bytes(raw)
                saved.append({"filename": document.original_filename, "path": str(path), "stored_name": stored, "temporary": True})

        conversation, _, _, response = await run_in_threadpool(
            service.send_message,
            user.id,
            query.strip(),
            conversation_id,
            attachments=saved,
        )

    except httpx.HTTPStatusError as exc:
        for item in saved:
            Path(item["path"]).unlink(missing_ok=True)

        return original_response(exc.response)

    except httpx.TimeoutException as exc:
        for item in saved:
            Path(item["path"]).unlink(missing_ok=True)

        raise HTTPException(
            status_code=504,
            detail="Maira request timed out",
        ) from exc

    except httpx.RequestError as exc:
        for item in saved:
            Path(item["path"]).unlink(missing_ok=True)

        raise HTTPException(
            status_code=502,
            detail="Could not connect to Maira",
        ) from exc

    except LookupError as exc:
        for item in saved:
            Path(item["path"]).unlink(missing_ok=True)

        raise HTTPException(
            status_code=404,
            detail=str(exc),
        ) from exc

    except ValueError as exc:
        for item in saved:
            Path(item["path"]).unlink(missing_ok=True)

        raise HTTPException(
            status_code=422,
            detail=str(exc),
        ) from exc

    except HTTPException:
        for item in saved:
            Path(item["path"]).unlink(missing_ok=True)

        raise

    except Exception as exc:
        for item in saved:
            Path(item["path"]).unlink(missing_ok=True)

        logger.exception(
            "Assistant request failed while processing uploaded files"
        )

        raise HTTPException(
            status_code=502,
            detail="Assistant request failed. Check backend logs.",
        ) from exc

    for item in saved:
        if item.get("temporary"):
            Path(item["path"]).unlink(missing_ok=True)
    invalidate_user(user.id)

    return original_response(
        response,
        conversation.id,
    )


def recording_to_wav(
    raw: bytes,
    suffix: str,
) -> bytes:
    if not shutil.which("ffmpeg"):
        raise HTTPException(
            status_code=503,
            detail=(
                "Voice recording needs FFmpeg. "
                "Use Docker or install ffmpeg."
            ),
        )

    with tempfile.TemporaryDirectory() as directory:
        source = Path(directory) / f"recording{suffix}"
        target = Path(directory) / "recording.wav"

        source.write_bytes(raw)

        try:
            subprocess.run(
                [
                    "ffmpeg",
                    "-nostdin",
                    "-v",
                    "error",
                    "-i",
                    str(source),
                    "-t",
                    "120",
                    "-ar",
                    "16000",
                    "-ac",
                    "1",
                    str(target),
                ],
                check=True,
                capture_output=True,
                timeout=30,
            )
        except (
            subprocess.SubprocessError,
            OSError,
        ) as exc:
            raise HTTPException(
                status_code=422,
                detail="Could not decode the microphone recording",
            ) from exc

        if not target.exists():
            raise HTTPException(
                status_code=422,
                detail="Audio conversion did not produce a WAV file",
            )

        return target.read_bytes()


def transcript_text(value, depth=0):
    """
    Extract transcript text from Chorus response structures.

    The known working response structure is:
    {
        "results": {
            "transcription": {
                "text": "recognized words"
            }
        }
    }
    """
    if depth > 20:
        return ""

    if isinstance(value, str):
        return value.strip()

    if isinstance(value, list):
        parts = [
            transcript_text(item, depth + 1)
            for item in value
        ]

        return " ".join(
            part for part in parts if part
        ).strip()

    if not isinstance(value, dict):
        return ""

    # IMPORTANT:
    # First handle the exact structure used by the working example:
    # task["results"]["transcription"]["text"]
    results = value.get("results")

    if isinstance(results, dict):
        transcription = results.get("transcription")

        if isinstance(transcription, dict):
            text_value = transcription.get("text")

            if isinstance(text_value, str) and text_value.strip():
                return text_value.strip()

        elif isinstance(transcription, str) and transcription.strip():
            return transcription.strip()

    # Also support other common Chorus response variants.
    text_keys = (
        "text",
        "transcript",
        "transcribed_text",
        "transcript_text",
        "recognized_text",
        "audio_text",
        "text_content",
        "sentence",
        "utterance",
    )

    for key in text_keys:
        candidate = value.get(key)

        if isinstance(candidate, str) and candidate.strip():
            return candidate.strip()

    # Search nested containers, including "results".
    container_keys = (
        "results",
        "transcription",
        "segments",
        "words",
        "content",
        "data",
        "result",
        "output",
        "task_result",
        "detail",
        "diarized_transcription",
    )

    for key in container_keys:
        candidate = value.get(key)

        if candidate is None:
            continue

        extracted = transcript_text(
            candidate,
            depth + 1,
        )

        if extracted:
            return extracted

    return ""


def _task_payload(result):
    """Return the task object when the API wraps it in detail."""
    if not isinstance(result, dict):
        return {}

    detail = result.get("detail")

    if isinstance(detail, dict):
        return {**result, **detail}

    return result


async def completed_transcription(
    client: httpx.AsyncClient,
    result,
    headers: dict[str, str],
    deadline: float,
):
    """Return a transcript or poll the Chorus task until it completes."""
    if not isinstance(result, dict):
        raise HTTPException(
            status_code=502,
            detail="Chorus returned an unexpected response format",
        )

    # Some API responses may include the transcript in the initial POST.
    text = transcript_text(result)

    if text:
        logger.info(
            "Chorus POST response already contained transcript text."
        )
        return {"text": text}

    task = _task_payload(result)
    task_id = task.get("task_id")

    if not task_id:
        logger.error(
            "Chorus POST response has no transcript or task_id. "
            "Response keys=%s",
            list(result.keys()),
        )

        raise HTTPException(
            status_code=502,
            detail=(
                "Chorus response did not contain "
                "a transcript or task ID"
            ),
        )

    logger.info(
        "Chorus transcription task accepted: task_id=%s",
        task_id,
    )

    task_url = (
        f"{CHORUS_SPEECHES_URL}/"
        f"{quote(str(task_id), safe='')}"
    )

    completed_statuses = {
        "success",
        "successful",
        "completed",
        "complete",
        "done",
    }

    failed_statuses = {
        "failed",
        "failure",
        "error",
        "cancelled",
        "canceled",
    }

    while time.monotonic() < deadline:
        remaining = deadline - time.monotonic()

        if remaining <= 0:
            break

        await asyncio.sleep(min(0.5, remaining))

        try:
            response = await client.get(
                task_url,
                headers=headers,
            )
            response.raise_for_status()

        except httpx.HTTPStatusError as exc:
            logger.error(
                "Chorus task polling failed: task_id=%s "
                "http_status=%s response=%s",
                task_id,
                exc.response.status_code,
                exc.response.text[:2000],
            )

            raise HTTPException(
                status_code=502,
                detail=(
                    "Chorus task polling failed "
                    f"(HTTP {exc.response.status_code})"
                ),
            ) from exc

        except httpx.RequestError as exc:
            logger.exception(
                "Network error while polling Chorus task_id=%s",
                task_id,
            )

            raise HTTPException(
                status_code=502,
                detail="Could not connect while checking Chorus task status",
            ) from exc

        try:
            task_result = response.json()

        except ValueError as exc:
            logger.error(
                "Chorus returned non-JSON task response: "
                "task_id=%s http_status=%s body=%s",
                task_id,
                response.status_code,
                response.text[:2000],
            )

            raise HTTPException(
                status_code=502,
                detail="Chorus returned an invalid task response",
            ) from exc

        task = _task_payload(task_result)
        status = str(
            task.get("status", "")
        ).strip().lower()

        # Extract transcript BEFORE handling the completed status.
        # This supports results.transcription.text.
        transcript = transcript_text(task_result)

        if transcript:
            logger.info(
                "Chorus transcript extracted: task_id=%s characters=%s",
                task_id,
                len(transcript),
            )

            return {"text": transcript}

        error_message = (
            task.get("error_message")
            or task.get("message")
            or task.get("error")
        )

        if status in failed_statuses:
            logger.error(
                "Chorus transcription failed: task_id=%s "
                "status=%s error=%s",
                task_id,
                status,
                error_message,
            )

            raise HTTPException(
                status_code=502,
                detail=(
                    "Chorus could not transcribe the recording: "
                    f"{error_message or status}"
                ),
            )

        if status in completed_statuses:
            # Avoid logging full transcript/audio metadata.
            # Log the response keys and transcript-related field types.
            results = task.get("results")
            transcription = (
                results.get("transcription")
                if isinstance(results, dict)
                else None
            )

            logger.error(
                "Chorus reports completion but no transcript "
                "could be extracted: task_id=%s status=%s "
                "top_keys=%s task_keys=%s results_type=%s "
                "transcription_type=%s",
                task_id,
                status,
                (
                    list(task_result.keys())
                    if isinstance(task_result, dict)
                    else type(task_result).__name__
                ),
                list(task.keys()),
                type(results).__name__,
                type(transcription).__name__,
            )

            raise HTTPException(
                status_code=502,
                detail=(
                    "Chorus finished but returned no extractable "
                    "transcript. Check the backend log for response keys."
                ),
            )

    logger.error(
        "Chorus transcription polling timed out: task_id=%s",
        task_id,
    )

    raise HTTPException(
        status_code=504,
        detail=(
            "Chorus transcription timed out. "
            "Please try a shorter recording."
        ),
    )


@router.post("/speech-to-text")
async def speech_to_text(
    request: Request,
    file: UploadFile = File(...),
    language: str = Form("auto"),
    task_type: str = Form("transcription"),
    initial_prompt: str = Form(""),
    user: User = Depends(require_roles("LandOfficer", "User")),
):
    require_csrf(request)

    suffix = Path(
        file.filename or "recording.wav"
    ).suffix.lower()

    allowed_audio = {
        ".wav",
        ".mp3",
        ".ogg",
        ".flac",
        ".m4a",
        ".aac",
        ".webm",
        ".mp4",
    }

    if suffix not in allowed_audio:
        raise HTTPException(
            status_code=415,
            detail="Unsupported audio format",
        )

    if task_type not in {
        "transcription",
        "diarization",
    }:
        raise HTTPException(
            status_code=422,
            detail="task_type must be transcription or diarization",
        )

    raw = await file.read()

    if not raw:
        raise HTTPException(
            status_code=422,
            detail="Recording is empty",
        )

    if len(raw) > settings.max_upload_mb * 1024 * 1024:
        raise HTTPException(
            status_code=413,
            detail="Audio file too large",
        )

    if (
        not settings.maira_api_key
        or not settings.maira_project_key
    ):
        raise HTTPException(
            status_code=503,
            detail="Maira speech service is not configured",
        )

    headers = {
        "api-key": settings.maira_api_key,
        "project-key": settings.maira_project_key,
    }

    filename = file.filename or "recording.wav"
    content_type = (
        file.content_type
        or "application/octet-stream"
    )

    if suffix in {".webm", ".mp4"}:
        raw = await run_in_threadpool(
            recording_to_wav,
            raw,
            suffix,
        )

        filename = "recording.wav"
        content_type = "audio/wav"

    upload_files = {
        "file": (
            filename,
            raw,
            content_type,
        )
    }

    data = {
        "task_type": task_type,
        "language": language,
        "initial_prompt": initial_prompt,
    }

    try:
        timeout_seconds = settings.maira_timeout_seconds
        deadline = time.monotonic() + timeout_seconds

        async with httpx.AsyncClient(
            timeout=timeout_seconds,
        ) as client:
            response = await client.post(
                CHORUS_SPEECHES_URL,
                headers=headers,
                files=upload_files,
                data=data,
            )

            response.raise_for_status()

            try:
                result = response.json()
            except ValueError as exc:
                logger.error(
                    "Chorus create-task response was not JSON: "
                    "http_status=%s body=%s",
                    response.status_code,
                    response.text[:2000],
                )

                raise HTTPException(
                    status_code=502,
                    detail="Chorus returned an invalid response",
                ) from exc

            transcript_result = await completed_transcription(
                client=client,
                result=result,
                headers=headers,
                deadline=deadline,
            )

        return transcript_result

    except httpx.HTTPStatusError as exc:
        logger.error(
            "Maira speech-to-text HTTP error: status=%s body=%s",
            exc.response.status_code,
            exc.response.text[:2000],
        )

        raise HTTPException(
            status_code=502,
            detail=(
                "Speech-to-text request failed "
                f"(HTTP {exc.response.status_code})"
            ),
        ) from exc

    except httpx.TimeoutException as exc:
        logger.exception("Maira speech-to-text request timed out")

        raise HTTPException(
            status_code=504,
            detail="Speech-to-text request timed out",
        ) from exc

    except httpx.RequestError as exc:
        logger.exception("Maira speech-to-text connection failed")

        raise HTTPException(
            status_code=502,
            detail="Could not connect to Maira speech service",
        ) from exc


@router.delete(
    "/conversations/{conversation_id}",
    status_code=204,
)
def delete_conversation(
    conversation_id: str,
    request: Request,
    user: User = Depends(require_roles("LandOfficer", "User")),
    service: Any = Depends(get_chat_service),
):
    require_csrf(request)

    try:
        service.delete_conversation(
            conversation_id,
            user.id,
        )
    except LookupError as exc:
        raise HTTPException(
            status_code=404,
            detail=str(exc),
        ) from exc

    invalidate_user(user.id)
    return None