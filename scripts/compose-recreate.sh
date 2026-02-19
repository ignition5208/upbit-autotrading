#!/usr/bin/env bash
set -euo pipefail
# code 반영은 recreate
docker compose --env-file .env up -d --build --force-recreate
