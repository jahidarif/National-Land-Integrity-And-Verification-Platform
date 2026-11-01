# Build notes — source reuse and implementation order

## Source reuse summary

1. Project A remains the base repository; its FastAPI application, cookie/JWT authentication skeleton, refresh-token rotation, CSRF handling, Maira passthrough, chat history, attachment validation, speech-to-text route and DemoAssistant fallback were retained.
2. Project A's Vue 3 application and dark-glass design were retained and extended rather than replaced.
3. Project B was used as a pattern reference for onion-style folder boundaries, dependency wiring, pagination envelopes, DTO validation, password hashing, seeding, route guards, Vuex namespacing and reusable form/table components.
4. Project B's live-PostgreSQL-only test was not copied; the new backend tests use in-memory SQLite and dependency overrides.
5. The supplied `models.py` is the authoritative entity specification; the original is preserved under `reference/`, and the implementation model lives in `backend/app/domain/models.py`.
6. Proposal v2.1 is treated as product background only; the v4 Markdown prompt takes precedence.
7. The Maira JSON is retained in `data/`; the optional importer reads only `authoritative_structured_land_record` from each entry.
8. The new backend scope adds areas, officers, lands, owners, transactions, officer drafts, User documents, private S3/MinIO storage and an inactive land-change publisher seam.
9. The new frontend scope adds role dashboards, full land detail panels, draft workflows, the User Documents page and a multi-window chat dock.
10. Live platform-to-Maira sync, OCR, automatic verification, source connectors and institutional access remain out of scope.

## Build sequence completed

- Backend foundation, data models, Alembic migration 0002 and role/auth seed.
- Admin area/officer management and server-side area lookup.
- Officer land CRUD, `ApplyLandUpsert`, value-set validation and no-op publisher seam.
- Officer create/update drafts, stale detection and publish operations.
- User owner-scoped land reads and computed `ownedLandIds`.
- User-only S3 Documents endpoints, MinIO Compose services and stored-document chat attachments.
- Chat role guards, stored document IDs and multi-window dock.
- Vue role shell, glass styles, reusable icon/form/modal/pagination components, feature Vuex modules and role pages.
- Backend tests, populated-database migration round-trip test, optional JSON importer and documentation.

## Known incomplete architecture work

The new v4 support, port, S3, DTO and use-case modules follow the one-class/one-public-operation convention. Some retained Project A compatibility code still has multi-operation classes: `application/services.py`, `domain/repositories.py`, `infrastructure/repositories.py` and `infrastructure/unit_of_work.py`. The current structure test checks the new v4 modules, not the entire backend tree. These compatibility modules still need a complete repository-per-operation/use-case decomposition before claiming full conformance with the prompt's global structure test.

## Environment validation

- Backend: `pytest -q` and Python compile checks.
- Migration: upgrade/downgrade against a populated SQLite database with existing chat rows.
- Optional import: run twice against SQLite and verify idempotent counts.
- Frontend TypeScript: syntax transpilation of TypeScript files and Vue `<script setup lang="ts">` blocks.
- Docker Compose: YAML parsed successfully. Docker engine was not available for an actual container build.
- Frontend: a full Vue production build could not be run because npm dependency installation was unavailable in the offline environment.

The frontend also has service modules and Vuex feature folders, but some role views still call their service wrappers directly. Authentication and chat are action-driven; the remaining Admin/Officer/User view reads and writes need to be routed through Vuex actions to satisfy the prompt's strict component/store boundary.


## Follow-up UI/runtime fixes (2026-11-01)
- Fixed the missing `()` invocation on the `defineEmits` compiler macro in `ChatWindow.vue`.
- Replaced the invalid React-style fragment in `ChatDock.vue` with a valid Vue root wrapper.
- Corrected officer update payloads to send only `fullName`, `assignedAreaId`, and `isActive`; email/password are not accepted by the update schema.
- Added shared dark-glass form control styling and a reusable global error dialog via `notify(message, 'error')` / `ToastHost`.
- Existing `SearchableSelect` already closes its options panel after selection; native HTML selects close on selection by browser behavior.
- Frontend build must be run in an environment with installed npm dependencies to verify compilation and integration.
