
from app.core.config import settings
from tests.conftest import csrf


def test_chat_accepts_and_persists_allowed_attachment(authenticated_client, tmp_path):
    response = authenticated_client.post(
        "/api/v1/chat/messages-with-files",
        headers=csrf(authenticated_client),
        data={"query": "Please explain this sample"},
        files=[
            (
                "files",
                ("sample.pdf", b"%PDF-1.4 fake test bytes", "application/pdf"),
            )
        ],
    )

    assert response.status_code == 200, response.text

    conversation_id = response.headers["X-Conversation-ID"]
    history = authenticated_client.get(
        f"/api/v1/chat/conversations/{conversation_id}"
    ).json()

    assert history["messages"][0]["content"] == "Please explain this sample"

    stored = list((tmp_path / "uploads").glob("*.pdf"))
    assert len(stored) == 1
    assert stored[0].read_bytes().startswith(b"%PDF")


def test_chat_rejects_unsupported_attachment(authenticated_client, tmp_path):
    response = authenticated_client.post(
        "/api/v1/chat/messages-with-files",
        headers=csrf(authenticated_client),
        data={"query": "Check this"},
        files=[
            (
                "files",
                ("payload.exe", b"not allowed", "application/octet-stream"),
            )
        ],
    )

    assert response.status_code == 415
    assert not list((tmp_path / "uploads").glob("*"))


def test_speech_to_text_requires_provider_credentials(
    authenticated_client, monkeypatch
):
    monkeypatch.setattr(settings, "maira_api_key", "")
    monkeypatch.setattr(settings, "maira_project_key", "")

    response = authenticated_client.post(
        "/api/v1/chat/speech-to-text",
        headers=csrf(authenticated_client),
        files={"file": ("voice.wav", b"RIFFtest", "audio/wav")},
    )

    assert response.status_code == 503


def test_speech_to_text_calls_provider(authenticated_client, monkeypatch):
    monkeypatch.setattr(settings, "maira_api_key", "test-api-key")
    monkeypatch.setattr(settings, "maira_project_key", "test-project-key")

    calls = {}

    class FakeResponse:
        status_code = 200
        text = ""

        def raise_for_status(self):
            return None

        def json(self):
            return {"detail": {"text": "Check the land record"}}

    class FakeAsyncClient:
        def __init__(self, timeout):
            calls["timeout"] = timeout

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            return False

        async def post(self, url, headers, files, data):
            calls.update(
                url=url,
                headers=headers,
                files=files,
                data=data,
            )
            return FakeResponse()

    import app.presentation.chat_router as router_module

    monkeypatch.setattr(
        router_module.httpx,
        "AsyncClient",
        FakeAsyncClient,
    )

    response = authenticated_client.post(
        "/api/v1/chat/speech-to-text",
        headers=csrf(authenticated_client),
        data={
            "language": "auto",
            "task_type": "transcription",
            "initial_prompt": "Bangladesh land records",
        },
        files={
            "file": (
                "voice.wav",
                b"RIFFtest-audio",
                "audio/wav",
            )
        },
    )

    assert response.status_code == 200, response.text

    # The endpoint normalizes provider output to {"text": "..."}.
    assert response.json() == {"text": "Check the land record"}

    assert calls["url"].endswith("/v1/speeches")
    assert calls["headers"]["api-key"] == "test-api-key"
    assert calls["headers"]["project-key"] == "test-project-key"
    assert calls["data"]["task_type"] == "transcription"
    assert calls["data"]["language"] == "auto"
    assert calls["data"]["initial_prompt"] == "Bangladesh land records"


def test_audio_upload_size_is_enforced(authenticated_client, monkeypatch):
    monkeypatch.setattr(
        settings,
        "max_upload_mb",
        0,
    )

    response = authenticated_client.post(
        "/api/v1/chat/speech-to-text",
        headers=csrf(authenticated_client),
        files={"file": ("voice.wav", b"audio", "audio/wav")},
    )

    assert response.status_code == 413


def test_speech_to_text_rejects_unsupported_format(
    authenticated_client, monkeypatch
):
    monkeypatch.setattr(settings, "maira_api_key", "test-api-key")
    monkeypatch.setattr(settings, "maira_project_key", "test-project-key")

    response = authenticated_client.post(
        "/api/v1/chat/speech-to-text",
        headers=csrf(authenticated_client),
        files={
            "file": (
                "voice.exe",
                b"not audio",
                "application/octet-stream",
            )
        },
    )

    assert response.status_code == 415


def test_speech_to_text_rejects_invalid_task_type(
    authenticated_client, monkeypatch
):
    monkeypatch.setattr(settings, "maira_api_key", "test-api-key")
    monkeypatch.setattr(settings, "maira_project_key", "test-project-key")

    response = authenticated_client.post(
        "/api/v1/chat/speech-to-text",
        headers=csrf(authenticated_client),
        data={"task_type": "summarization"},
        files={"file": ("voice.wav", b"audio", "audio/wav")},
    )

    assert response.status_code == 422


def test_chat_rejects_more_than_five_attachments(authenticated_client, tmp_path):
    files = [
        ("files", (f"sample-{i}.txt", b"content", "text/plain"))
        for i in range(6)
    ]

    response = authenticated_client.post(
        "/api/v1/chat/messages-with-files",
        headers=csrf(authenticated_client),
        data={"query": "Inspect these"},
        files=files,
    )

    assert response.status_code == 422
    assert not list((tmp_path / "uploads").glob("*"))


def test_chat_cleans_already_saved_files_when_later_file_is_rejected(
    authenticated_client, tmp_path
):
    response = authenticated_client.post(
        "/api/v1/chat/messages-with-files",
        headers=csrf(authenticated_client),
        data={"query": "Inspect these"},
        files=[
            ("files", ("first.txt", b"safe", "text/plain")),
            (
                "files",
                ("blocked.exe", b"not safe", "application/octet-stream"),
            ),
        ],
    )

    assert response.status_code == 415
    assert not list((tmp_path / "uploads").glob("*"))


def test_speech_to_text_provider_failure_returns_bad_gateway(
    authenticated_client, monkeypatch
):
    import httpx
    import app.presentation.chat_router as router_module

    monkeypatch.setattr(settings, "maira_api_key", "test-api-key")
    monkeypatch.setattr(settings, "maira_project_key", "test-project-key")

    class FakeAsyncClient:
        def __init__(self, timeout):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            return False

        async def post(self, *args, **kwargs):
            raise httpx.ConnectError("provider unavailable")

    monkeypatch.setattr(
        router_module.httpx,
        "AsyncClient",
        FakeAsyncClient,
    )

    response = authenticated_client.post(
        "/api/v1/chat/speech-to-text",
        headers=csrf(authenticated_client),
        files={"file": ("voice.wav", b"audio bytes", "audio/wav")},
    )

    assert response.status_code == 502

    # Match the actual connection-error message in chat_router.py.
    assert response.json()["detail"] == (
        "Could not connect to Maira speech service"
    )


def test_browser_webm_is_converted_before_chorus_call(
    authenticated_client, monkeypatch
):
    import app.presentation.chat_router as module
    import httpx

    monkeypatch.setattr(settings, "maira_api_key", "test-key")
    monkeypatch.setattr(settings, "maira_project_key", "test-project")
    monkeypatch.setattr(
        module,
        "recording_to_wav",
        lambda raw, suffix: b"RIFF-converted-wave",
    )

    captured = {}

    class FakeClient:
        def __init__(self, **kwargs):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            pass

        async def post(self, url, headers, files, data):
            captured.update(
                url=url,
                headers=headers,
                files=files,
                data=data,
            )

            return httpx.Response(
                200,
                json={"text": "My spoken query"},
                request=httpx.Request("POST", url),
            )

    monkeypatch.setattr(module.httpx, "AsyncClient", FakeClient)

    response = authenticated_client.post(
        "/api/v1/chat/speech-to-text",
        headers=csrf(authenticated_client),
        files={
            "file": (
                "recording.webm",
                b"browser-audio",
                "audio/webm",
            )
        },
    )

    assert response.status_code == 200, response.text
    assert response.json() == {"text": "My spoken query"}

    assert captured["files"]["file"] == (
        "recording.wav",
        b"RIFF-converted-wave",
        "audio/wav",
    )

    # Transcription must not create a chat or automatically call Ask.
    assert authenticated_client.get(
        "/api/v1/chat/conversations"
    ).json() == []


def test_chorus_background_task_is_polled_until_transcript(
    authenticated_client, monkeypatch
):
    import app.presentation.chat_router as module
    import httpx

    monkeypatch.setattr(settings, "maira_api_key", "test-key")
    monkeypatch.setattr(settings, "maira_project_key", "test-project")

    calls = []

    async def no_delay(_):
        pass

    monkeypatch.setattr(module.asyncio, "sleep", no_delay)

    class FakeClient:
        def __init__(self, **kwargs):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            pass

        async def post(self, url, **kwargs):
            return httpx.Response(
                202,
                json={"detail": {"task_id": "speech-123"}},
                request=httpx.Request("POST", url),
            )

        async def get(self, url, headers):
            calls.append(url)

            return httpx.Response(
                200,
                json={
                    "detail": {
                        "status": "success",
                        "result": {"text": "Recorded question"},
                    }
                },
                request=httpx.Request("GET", url),
            )

    monkeypatch.setattr(module.httpx, "AsyncClient", FakeClient)

    response = authenticated_client.post(
        "/api/v1/chat/speech-to-text",
        headers=csrf(authenticated_client),
        files={
            "file": (
                "recording.wav",
                b"RIFF-audio",
                "audio/wav",
            )
        },
    )

    assert response.status_code == 200, response.text

    # Polling extracts the transcript and returns the normalized format.
    assert response.json() == {"text": "Recorded question"}
    assert calls
    assert calls[0].endswith("/v1/speeches/speech-123")
