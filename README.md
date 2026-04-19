# SmartLock — Authentication & Authorization

Core authentication and authorization service for the DeVinci Fablab smart locker system. Built with FastAPI, Keycloak, and PostgreSQL.

## What this service does

- Validates NFC badge scans against Keycloak user attributes and locker permissions
- Exposes a REST API for managing lockers, items, stock, categories, and access permissions
- Proxies Keycloak user/group reads for the admin dashboard
- Records an audit log of every locker access attempt

## Architecture

```
[Raspberry Pi / NFC] --> POST /auth/locker/{id}/check --> [FastAPI] --> [PostgreSQL]
[Admin Dashboard]    --> API calls (admin JWT)        --> [FastAPI] --> [Keycloak Admin API]
                                                                    --> [Keycloak]
```

See [`docs/system-design.md`](docs/system-design.md) for the full architecture.

---

## Documentation

| Document | Description |
|---|---|
| [`docs/deployment.md`](docs/deployment.md) | Full server deployment guide (SSH commands, step-by-step) |
| [`docs/keycloak-test-guide.md`](docs/keycloak-test-guide.md) | Keycloak realm, clients, roles, and groups setup |
| [`docs/api-reference.md`](docs/api-reference.md) | All API endpoints with request/response examples |
| [`docs/guide-admin-dashboard.md`](docs/guide-admin-dashboard.md) | Frontend integration guide (admin dashboard) |
| [`docs/guide-locker-client.md`](docs/guide-locker-client.md) | Raspberry Pi / NFC client integration guide |
| [`docs/system-design.md`](docs/system-design.md) | System architecture, auth flows, data model |

---

## Quick Start (local development)

### Prerequisites

- Docker & Docker Compose
- Git

### Run locally

```bash
git clone https://github.com/DeVinci-FabLab/SmartLock-Authentication-Authorization.git
cd SmartLock-Authentication-Authorization/docker/database

cp .env.example .env
# Edit .env — set POSTGRES_PASSWORD, KEYCLOAK_URL, secrets, etc.

docker compose up smartlock-api-dev postgres -d
```

API available at `http://localhost:8000` — Swagger UI at `http://localhost:8000/docs`.

Database migrations run automatically on container start.

---

## Production Deployment

See [`docs/deployment.md`](docs/deployment.md) for the complete step-by-step guide.

Summary:
1. Deploy Keycloak (`docker/keycloak/compose.yml`)
2. Configure realm, clients, roles, groups — see [`docs/keycloak-test-guide.md`](docs/keycloak-test-guide.md)
3. Deploy API + PostgreSQL (`docker/database/compose.yml`, production service)
4. CD pipeline (`.github/workflows/CD.yml`) builds and pushes the image to GHCR on every push to `main`
5. Watchtower handles automatic updates

**Production URL:** `https://api.smartlock.devinci-fablab.fr`

---

## Environment Variables

Copy `docker/database/.env.example` to `docker/database/.env` and fill in:

| Variable | Description |
|---|---|
| `POSTGRES_USER` / `POSTGRES_PASSWORD` / `POSTGRES_DB` | PostgreSQL credentials |
| `DATABASE_URL` | Full connection string (use the values above) |
| `KEYCLOAK_URL` | Keycloak base URL (e.g. `https://auth.devinci-fablab.fr`) |
| `KEYCLOAK_REALM` | Realm name |
| `KEYCLOAK_CLIENT_SECRET` | Secret for `smartlock-api` client |
| `LOCKER_CLIENT_SECRET` | Secret for `smartlock-lockers` service account |
| `NFC_CLIENT_SECRET` | Secret for `nfc-scanner` service account |
| `CORS_ORIGINS` | JSON array of allowed origins (e.g. `["https://dashboard.devinci-fablab.fr"]`) |
| `VOLUMES_PATH` | Docker volume base path (default: `/home/debian/docker/volumes`) |

---

## Database Migrations

Migrations run automatically on container start via `entrypoint.sh` (`alembic upgrade head`).

To generate a new migration after changing SQLAlchemy models:

```bash
docker compose exec smartlock-api-dev uv run alembic revision --autogenerate -m "description"
```

To view migration history:

```bash
docker compose exec smartlock-api-dev uv run alembic history
```

---

## Security & Maintenance

### Rate Limiting

`slowapi` rate limits are applied per endpoint. Adjust limits via the `@limiter.limit(...)` decorators in `src/routes/`.

### Logging

All requests are traced by `src/utils/middleware_logger.py`. Logs are written by `loguru`.

```bash
docker compose logs smartlock-api --tail=100 -f
```

### Database Backup

```bash
docker exec smartlock-postgres pg_dump -U <POSTGRES_USER> <POSTGRES_DB> > backup_$(date +%Y%m%d).sql
```

### Security hardening applied

- `security_opt: no-new-privileges:true` on all containers
- CORS origins configurable via `CORS_ORIGINS` env var (no wildcard in production)
- Traefik handles TLS termination
- Watchtower auto-updates images from GHCR on new pushes to `main`
