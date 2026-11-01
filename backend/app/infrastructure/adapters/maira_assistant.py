from __future__ import annotations

import json
import mimetypes
from pathlib import Path

import httpx

from app.domain.ports.i_assistant_provider import IAssistantProvider
from app.core.config import settings

# Use the exact Ask endpoint supplied for this project. Original .env files
# are preserved, including their older MAIRA_ASK_URL value.
MAIRA_ASK_URL = "https://api.maira.gigalogy.com/client/v1/maira/ask"
MAIRA_FILES_URL = "https://api.maira.gigalogy.com/client/v1/maira/iask"


def extract_response_text(payload) -> str:
    """Read an answer for saved history only; the HTTP body is returned intact."""
    if isinstance(payload, str):
        return payload
    if isinstance(payload, dict):
        for key in ("response", "answer", "text", "content", "message"):
            if isinstance(payload.get(key), str):
                return payload[key]
        for key in ("detail", "data", "result", "output"):
            if isinstance(payload.get(key), (dict, list)):
                text = extract_response_text(payload[key])
                if text:
                    return text
    if isinstance(payload, list):
        return "\n".join(filter(None, (extract_response_text(item) for item in payload)))
    return ""


class MairaAssistant(IAssistantProvider):
    def ask(self, query: str, history=None, files=None, session_id=None) -> httpx.Response:
        if not settings.maira_api_key or not settings.maira_project_key:
            raise RuntimeError("MAIRA_API_KEY or MAIRA_PROJECT_KEY is missing")
        if not settings.maira_gpt_profile_id:
            raise RuntimeError("MAIRA_GPT_PROFILE_ID is missing")

        headers = {
            "project-key": settings.maira_project_key,
            "api-key": settings.maira_api_key,
        }
        payload = {
            "user_id": settings.maira_user_id,
            "query": query,
            "conversation_type": "question",
            "gpt_profile_id": settings.maira_gpt_profile_id,
        }
        with httpx.Client(timeout=settings.maira_timeout_seconds) as client:
            if files:
                uploads = [
                    (
                        "files",
                        (
                            item["filename"],
                            Path(item["path"]).read_bytes(),
                            mimetypes.guess_type(item["filename"])[0] or "application/octet-stream",
                        ),
                    )
                    for item in files
                ]
                # The same four-field JSON, with raw files in separate parts.
                # Let httpx supply the multipart Content-Type and boundary.
                response = client.post(
                    MAIRA_FILES_URL,
                    headers=headers,
                    data={"payload": json.dumps(payload)},
                    files=uploads,
                )
            else:
                response = client.post(
                    MAIRA_ASK_URL,
                    headers={**headers, "Content-Type": "application/json"},
                    json=payload,
                )
        response.raise_for_status()
        return response
