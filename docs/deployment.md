# Deployment Guide — SmartLock Authentication & Authorization

## Prerequisites

The target server must already have:
- Docker & Docker Compose installed
- **Traefik** running and connected to an external Docker network named `traefik-network`
- **Watchtower** running (for automatic image updates)
- The server environment variable `VOLUMES_PATH` set (e.g., `/home/debian/docker/volumes`)
- DNS A-records pointing to the server IP:
  - `auth.devinci-fablab.fr` → Keycloak
  - `api.smartlock.devinci-fablab.fr` → SmartLock API

---

## First-Time Setup

Clone the repository on the server:

```bash
git clone https://github.com/DeVinci-FabLab/SmartLock-Authentication-Authorization.git
cd SmartLock-Authentication-Authorization
```

---

## Step 1 — Deploy Keycloak

```bash
cd docker/keycloak

cp .env.example .env
```

Edit `.env` and set secure values for:
- `VOLUMES_PATH` — should match the server's `$VOLUMES_PATH` (or omit to rely on the env variable)
- `POSTGRES_PASSWORD` — generate with `openssl rand -base64 32`
- `KC_BOOTSTRAP_ADMIN_PASSWORD` — generate with `openssl rand -base64 32`
- `KC_HOSTNAME` — `auth.devinci-fablab.fr`

Create the required volume directories:

```bash
mkdir -p ${VOLUMES_PATH}/keycloak/conf
mkdir -p ${VOLUMES_PATH}/keycloak/postgres_data
```

Start Keycloak:

```bash
docker compose up -d
```

Verify it is healthy (takes ~2 minutes on first start):

```bash
docker compose ps
# keycloak_web should show "healthy"
```

Keycloak admin console is available at `https://auth.devinci-fablab.fr`.

---

## Step 2 — Configure Keycloak Realm & Clients

Log in to the Keycloak admin console and set up the realm, roles, and service accounts as described in [`keycloak-test-guide.md`](./keycloak-test-guide.md).

Required clients to create:
- `smartlock-api` — the FastAPI backend (confidential client)
- `smartlock-lockers` — locker hardware service account
- `nfc-scanner` — NFC reader service account

Copy the generated client secrets — you will need them for the API `.env`.

---

## Step 3 — Deploy the SmartLock API

```bash
cd docker/database

cp .env.example .env
```

Edit `.env` and set:
- `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_DB` — choose secure values
- `DATABASE_URL` — `postgresql://<user>:<password>@postgres:5432/<db>` (use the same values as above)
- `KEYCLOAK_URL` — `https://auth.devinci-fablab.fr`
- `KEYCLOAK_REALM` — your realm name
- `KEYCLOAK_CLIENT_SECRET` — from Step 2
- `LOCKER_CLIENT_SECRET`, `NFC_CLIENT_SECRET` — from Step 2
- `CORS_ORIGINS` — `["https://your-frontend-domain.fr"]`
- `VOLUMES_PATH` — same as the server's `$VOLUMES_PATH`

Create the required volume directory:

```bash
mkdir -p ${VOLUMES_PATH}/smartlock_auth/postgres_data
```

The production service pulls the image automatically from GHCR (built by the CD pipeline on every push to `main`). Start it:

```bash
docker compose up smartlock-api postgres -d
```

> **Note:** Use the `smartlock-api` service (image-based), not `smartlock-api-dev` (build-based), on the server.

Database migrations run automatically on container start via `entrypoint.sh`.

---

## Step 4 — Verify

Check all services are healthy:

```bash
docker compose ps
```

Test the API health endpoint:

```bash
curl https://api.smartlock.devinci-fablab.fr/health
# Expected: {"status": "ok", ...}
```

Check Traefik dashboard to confirm both `keycloak` and `smartlock-auth` routers show green with valid TLS certificates.

---

## Updates

Watchtower is configured on both services with `com.centurylinklabs.watchtower.enable=true`. When a new commit is pushed to `main`, the CD pipeline builds and pushes a new image to GHCR, and Watchtower will automatically pull and restart the container within its polling interval.

To force an immediate update:

```bash
docker compose pull smartlock-api && docker compose up smartlock-api -d
```

---

## Database Backups

Back up the PostgreSQL data directory or use `pg_dump`:

```bash
docker exec smartlock-postgres pg_dump -U <user> <db> > backup_$(date +%Y%m%d).sql
```

---

## Local Development

To run the stack locally (builds from source):

```bash
cd docker/database
cp .env.example .env
# Edit .env with local values (ENVIRONMENT=development, DEBUG=True, etc.)

docker compose up smartlock-api-dev postgres -d
```

The API is available at `http://localhost:8000` and Swagger docs at `http://localhost:8000/docs`.
