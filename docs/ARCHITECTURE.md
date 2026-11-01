# NLI Platform Architecture (v4)

## Layers and dependency direction

The backend follows an onion-style dependency direction: presentation routers call application use cases; use cases depend on domain ports and repository contracts; infrastructure adapters implement persistence, hashing, JWT, assistant and S3 concerns. FastAPI dependency factories in `app/presentation/deps.py` are the composition root. ORM entities are centralized in `app/domain/models.py` as the explicit model-file exemption.

The v4 convention is one class per file and one public operation per class (with `__init__` permitted). DTOs and data-only value objects are separate files. Routers remain transport adapters; no use case should import FastAPI, SQLAlchemy or boto3.

## Roles and server-side scope

- Admin manages Land Officers and Areas; Admin cannot access land endpoints or chat.
- Land Officers can access records and drafts for their currently assigned area only. Assignment is read from the database for each request.
- Users can read lands where their authenticated email is a `land_owners.owner_email` and manage only their own Documents.
- Role is selected at account creation and is not editable. Admin is seeded from environment variables.

## Land drafts

An update draft is keyed by `land_id` and stores the whole form payload plus the `lands.updated_at` value captured at first save. Later saves preserve that base timestamp. Publishing compares the current land timestamp and returns 409 for a stale draft. A create draft has its own UUID and stores the officer's area on the server. Draft writes never touch final land, owner or transaction rows and never emit change events. Publishing applies the complete validated payload in one database transaction, removes the draft and emits one change event after commit.

## Documents

A User document has metadata in PostgreSQL and bytes in a private S3 bucket. Storage keys are never returned to browsers. Upload validates extension, declared content type, magic bytes and size; writes the object with AES256 server-side encryption; then inserts metadata. If metadata insertion fails, the object write is compensated. Deletion commits metadata removal before attempting object deletion. Presigned GET URLs are short-lived. Local development uses MinIO and a one-shot bucket initialization service.

## Chat and Maira

The existing `/api/v1/chat/*` contract, provider passthrough, response status/body and `X-Conversation-ID` behavior are retained. Chat is available to Users and Land Officers, not Admin. A User can explicitly attach up to five local files and/or their own stored document IDs. Stored documents are owner-scoped and revalidated before being forwarded. No platform land data is sent to Maira. Maira remains on demo-trained synthetic data; the database and demo assistant remain disconnected.

## Planned sync seam (inactive)

Final land creates and updates publish a `LandChangeEvent` through `ILandChangePublisher`. The default adapter is `NoopLandChangePublisher`; it performs no network or data synchronization. A future release may add an approved privacy-filtered snapshot builder and Maira sync publisher after data-sharing, privacy and security approvals. Neither is implemented in this build.

## Compatibility boundary / remaining refactor

The new v4 domain value objects, ports, `ApplyLandUpsert`, `NormalizeArea`, `PublishLandChange`, S3 adapters and DTO modules follow the one-class/one-public-operation convention and are covered by `tests/test_backend_structure.py`. To preserve Project A's working authentication and chat contract during this extension, several pre-existing Project A compatibility modules (`application/services.py`, `domain/repositories.py`, `infrastructure/repositories.py`, `infrastructure/unit_of_work.py`, and existing auth/chat adapters) remain in their original multi-operation form. The platform router also still contains some endpoint-level persistence and orchestration that should move into thin router → use-case → repository calls. They are functional compatibility code, but have not yet been fully decomposed into the complete v4 use-case/repository-per-operation catalogue. A strict full-repository architecture audit would therefore still flag those retained files. This is a known implementation gap rather than a claim of full structural compliance.

## Product decisions to confirm before production

- The build prompt explicitly permits self-registration as a Land Officer. If officer accounts should be Admin-created only, registration policy must be changed before production.
- The User view currently returns every recorded field on an owned parcel, including other recorded owners' email addresses and share percentages, because the prompt requires every recorded field. Confirm this disclosure policy with the data owner before using real citizen records.
- The seeded Admin credentials are development defaults only. Replace them and the JWT secret before any shared deployment.

On the frontend, feature service modules and namespaced Vuex module folders are present. Authentication and chat use Vuex actions, but several Admin/Officer/User views still call their feature service wrapper directly rather than dispatching every read/write through Vuex. A final frontend state-management pass is still needed to satisfy the prompt's strict “components only dispatch actions and read getters” rule.
