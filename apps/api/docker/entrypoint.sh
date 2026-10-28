#!/usr/bin/env sh
set -eu

# Apply schema before the app process starts so lifespan seeds and routes
# never race an unmigrated database (local, staging, or production).
alembic upgrade head

exec "$@"
