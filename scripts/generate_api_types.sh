#!/usr/bin/env sh
set -eu

ROOT="$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)"
cd "$ROOT"

docker compose exec -T api python -m scripts.export_openapi
docker compose exec -T web npm run generate:api
