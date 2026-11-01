# Verification

- Backend: **41 tests passed** using SQLite and mocked Maira/Chorus HTTP calls.
- Vue production build: passed.
- Mocked frontend flow: passed (record/stop, transcript input, manual send, query-only JSON, multipart query/files, cleanup and error recovery).
- Live browser test: not run; browser runtime unavailable.
- Original `backend/.env`, `frontend/.env`, and all `.env.example` files: byte-for-byte comparison with the input ZIP passed.

Tests cover authentication/CSRF, conversation ownership and history, cache invalidation, exact four-field Ask JSON, configured provider user/profile IDs, original provider response bytes and status on both Ask routes, provider error passthrough, original attachment byte/name/MIME forwarding, typed-query preservation, empty queries with files, upload cleanup, recorded WebM-to-WAV forwarding, and deferred speech transcription tasks.

```bash
cd backend
uv sync --group dev
uv run pytest -q
```

Live Maira/Chorus calls are not part of these tests. Docker image builds were not run in this environment.
