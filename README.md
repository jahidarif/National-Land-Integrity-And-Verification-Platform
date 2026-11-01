# National Land Integrity & Verification Platform — v4

A role-based land-record management platform extended from the supplied National Land Integrity Chatbot. The base FastAPI/Vue 3 application, its Maira passthrough, saved chat history and voice input are retained. The new platform adds Admin, Land Officer and User views, managed land records, officer drafts and private user Documents storage.

> **Demo-data notice:** all supplied land records and PDFs are synthetic demonstration material. This is not a government service, an official certificate issuer or a legal verification authority.

## Current scope

- **Admin:** manage Land Officer accounts; create/update areas; assign, reassign and unassign officer areas.
- **Land Officer:** access lands only in the currently assigned area; search by owner email; create/update final land records; save, edit, delete and publish new-land and update drafts.
- **User:** read lands whose `land_owners.owner_email` matches the signed-in email; upload, list, view and delete personal Documents.
- **Chat:** role-limited Maira chat dock for Users and Land Officers, with multiple windows, local file attachments and explicitly selected stored User documents.
- **Storage:** PostgreSQL metadata plus private S3-compatible object storage. MinIO is included for local development.

### Explicitly out of scope

There is no live platform-to-Maira synchronization, document OCR, automatic verification, document-to-land matching, source-system connector, versioned change history, bank/institutional API or Admin/Land Officer Documents page. Verification fields are entered by officers; they are not computed. The planned sync seam currently uses `NoopLandChangePublisher` and performs no network calls.

Maira continues to answer from its demo-trained synthetic dataset and remains disconnected from platform land records. Only files or stored documents that a User explicitly selects in a chat message are forwarded. No land-record data is sent to Maira.

## Stack

- Backend: Python 3.12/3.13, uv, FastAPI, SQLAlchemy 2 sync Session, PostgreSQL, Alembic, Pydantic v2, PyJWT, bcrypt, Gunicorn/Uvicorn, boto3.
- Frontend: Vue 3 Composition API, TypeScript, Vue Router 4, Vuex 4, Axios, Vue CLI/webpack, regular CSS.
- Local object store: MinIO (S3-compatible).

## Run with Docker Compose

1. Copy the environment examples:

   ```bash
   cp .env.example .env
   cp backend/.env.example backend/.env
   cp frontend/.env.example frontend/.env
   ```

2. In the root `.env`, replace `MINIO_ROOT_USER` and `MINIO_ROOT_PASSWORD` with local-only values. Replace the development `JWT_SECRET_KEY` before any shared deployment. The Admin seed values are development defaults and can be changed.
3. Start the stack:

   ```bash
   docker compose up --build
   ```

4. Open:
   - Frontend: http://localhost:8080
   - FastAPI docs: http://localhost:5000/docs
   - MinIO console: http://localhost:9001

Compose starts PostgreSQL and MinIO, waits for their health checks, runs a one-shot MinIO bucket initialization job, then starts the backend. The backend runs `alembic upgrade head`, executes the idempotent Admin seed and starts Gunicorn. MinIO bucket access is private (`anonymous set none`).

### Development Admin

The root `.env.example` includes development seed defaults:

Use the development email and password shown in `.env.example`. Change these values before using a shared environment. The seed reads `ADMIN_SEED_EMAIL`, `ADMIN_SEED_PASSWORD` and `ADMIN_SEED_NAME`; credentials are not embedded in application source. The Admin cannot self-register.

Users and Land Officers can register. A self-registered Land Officer starts unassigned and sees no lands until an Admin assigns an area. This is an explicit build assumption: officer self-registration is allowed rather than restricting officer creation to Admins.

## Run locally

Requires Python 3.12 or 3.13, uv, Node.js 20+, npm, PostgreSQL and a reachable S3-compatible bucket. For the full local storage workflow, start MinIO using the Compose service.

Backend:

```bash
cd backend
uv sync --group dev
uv run alembic upgrade head
uv run python scripts/seed.py
uv run uvicorn run:app --reload --host 0.0.0.0 --port 5000
```

Frontend, in another terminal:

```bash
cd frontend
npm ci
npm run serve
```

For browser voice support on Ubuntu, install FFmpeg if you use the recorded-audio speech-to-text route:

```bash
sudo apt-get install ffmpeg
```

## Documents storage configuration

The Documents feature is User-only. Allowed extensions are PDF, PNG, JPG, JPEG, TXT and CSV. Each file is limited by `MAX_UPLOAD_MB` (default 15 MB); each User is limited by `DOCUMENTS_MAX_PER_USER` (default 50). The backend checks extension, declared content type, file signature where applicable and size. Filenames are sanitized. Browser responses never include the S3 `storage_key`.

The bucket must be private, with all public access blocked. Uploads request `AES256` server-side encryption. Configure:

- `S3_BUCKET`
- `S3_REGION`
- `S3_ENDPOINT_URL` (optional; set to `http://minio:9000` in Compose)
- `S3_ACCESS_KEY_ID` and `S3_SECRET_ACCESS_KEY` (optional; otherwise boto3 uses its default credential chain)
- `S3_PRESIGN_EXPIRES_SECONDS` (default 300)

The `.env.example` files intentionally leave S3 credentials blank. Compose injects the local MinIO credentials from the root environment into the backend. For AWS, use an IAM role or dedicated least-privilege user. A starting policy for one private bucket is:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": ["s3:PutObject", "s3:GetObject", "s3:DeleteObject"],
      "Resource": "arn:aws:s3:::YOUR_PRIVATE_BUCKET/users/*"
    }
  ]
}
```

Also enable all four S3 Block Public Access settings and default bucket encryption. Do not grant `s3:ListBucket` unless a separate operational workflow requires it.

Upload flow: validate → upload object → insert metadata. If metadata insertion fails, the object write is compensated. Delete flow: commit metadata deletion → attempt object deletion; an S3 delete failure is logged without reversing the committed metadata deletion. Presigned GET links are short-lived and returned only after an owner-scoped lookup.

## Authentication and access rules

- Cookie JWT authentication uses HttpOnly access/refresh cookies, readable CSRF cookies and the `X-CSRF-TOKEN` header. The frontend first calls `GET /api/auth/csrf`; registration, login, refresh, logout and all protected write routes validate CSRF.
- Refresh tokens rotate by `jti`.
- Password length is 8–72 characters and hashing uses bcrypt.
- Email is lowercased and unique across all roles.
- Role is immutable; update DTOs do not accept a role.
- Officer area and User email filters are derived from the authenticated database identity, never from browser-supplied scope values.
- Admin cannot use land endpoints or chat.

## Chat and Maira

The existing `/api/v1/chat/*` endpoints, Maira passthrough body (`user_id`, `query`, `conversation_type`, `gpt_profile_id`), provider response body/status and `X-Conversation-ID` header are retained. Chat windows are independently bound to conversation IDs (maximum three by default). A User may select stored Documents in addition to local files; a Land Officer may attach local files only. The combined limit is five files, with the existing 15 MB per-file default.

Maira is optional. When `MAIRA_ENABLED=false`, the existing `DemoAssistant` is used. When enabled, configure the API/project keys and GPT profile ID in the backend environment. Do not send platform database contents or unselected documents.

## Optional synthetic demo import

The optional importer reads only each entry's `authoritative_structured_land_record` object from the supplied one-file JSON bundle. It upserts normalized areas, maps parcel/document/ownership/succession/case/mortgage/price/verification fields, creates synthetic placeholder owner emails and imports transaction rows. It does not import the authority PDFs, upload samples, policies or training text. Imported records are final records, not drafts.

Place the supplied file at `data/National_Land_Integrity_Maira_All_Data_One_JSON_ASCII_UTF8.json` or set `NLI_DEMO_JSON`, then run:

```bash
cd backend
uv run python scripts/import_demo_lands.py
```

## Tests and checks

```bash
cd backend
uv sync --group dev
uv run pytest -q
```

The backend suite currently has 59 passing tests and uses in-memory SQLite and does not require AWS or MinIO. It covers the retained chat/auth flows, role restrictions, Admin area/officer management, unassigned officer behavior, land creation/drafts/publishing, owner-scoped User land reads, role immutability, conflict mapping and the one-class/one-operation convention for new v4 modules (some original Project A compatibility modules remain multi-operation and the platform router is not yet fully thin; see `docs/ARCHITECTURE.md` and `docs/BUILD_NOTES.md`). The migration was also exercised against a populated SQLite database: existing chat messages and conversations remained after upgrade and downgrade.

The frontend uses the existing package-lock and no new dependencies. Run `npm ci && npm run build` in `frontend` in an environment with npm registry access. TypeScript source and Vue script blocks passed syntax transpilation (106 files); a production frontend build could not be run because the npm registry was unavailable. Docker Compose YAML was parsed, but no Docker engine was available for a container build.

## Architecture

See [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) for layer direction, the single-operation convention, draft flow, document flow and the inactive future sync seam.

## Supplied references

The `reference/` folder contains the v4 build prompt, the original authoritative `models.py`, Proposal v2.1 PDF, and the synthetic Maira JSON bundle used for this build. The current User response intentionally includes co-owner email/share fields as required by the prompt; confirm this disclosure policy before loading real citizen records.
