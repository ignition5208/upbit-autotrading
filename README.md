# Upbit ATS v2.0-0001

Local-first Docker-compose based Upbit auto-trading platform.

## Quick start
1) Create `.env` from `.env.example`
2) Build trader image once: `make trader-image`
3) `docker compose up -d --build`
4) Open: http://127.0.0.1:8080/dashboard/

## Notes
- Credentials are stored encrypted in MariaDB using Fernet (CRYPTO_MASTER_KEY).
- For local dev, API key auth is disabled.
