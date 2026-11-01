#!/bin/sh
set -eu
uv run alembic upgrade head
uv run python scripts/seed.py
exec uv run gunicorn -k uvicorn.workers.UvicornWorker --bind "0.0.0.0:${PORT:-5000}" --workers "${WEB_CONCURRENCY:-2}" --timeout 60 run:app
