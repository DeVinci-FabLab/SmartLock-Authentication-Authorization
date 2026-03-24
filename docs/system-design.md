# SmartLock System Design

## Overview

A fablab smart locker system where members tap an NFC card to get access. The system has two interaction paths:

1. **Locker path** — Raspberry Pi reads NFC card → calls API → gets access decision
2. **Dashboard path** — Admin logs in via browser (OIDC + OTP) → manages lockers, users, inventory

---

## Architecture Diagram

```plain
┌────────────────────────────────────────────────────────────────────┐
│                            Fablab Network                          │
│                                                                    │
│  ┌──────────────┐   POST /auth/locker/{id}/check   ┌───────────┐  │
│  │ Raspberry Pi │  ──────────────────────────────► │           │  │
│  │ (NFC reader) │  ◄──────────────────────────────  │ FastAPI   │  │
│  └──────────────┘   { allowed, permissions }       │   API     │  │
│                                                    │           │  │
│  ┌──────────────┐   API calls (admin JWT)          │           │  │
│  │   Svelte     │  ──────────────────────────────► │           │  │
│  │  Dashboard   │  ◄──────────────────────────────  │           │  │
│  └──────────────┘                                  └─────┬─────┘  │
│         │                                                │        │
│         │ OIDC / browser redirect                        │ Admin  │
│         ▼                                                │ REST   │
│  ┌─────────────┐                                         │ API    │
│  │  Keycloak   │ ◄───────────────────────────────────────┘        │
│  │  (fablab    │                                                   │
│  │   realm)    │                                                   │
│  └─────────────┘                                                   │
└────────────────────────────────────────────────────────────────────┘
```

---

## Keycloak Setup (Realm: `fablab`)

### Why roles instead of groups for permissions

In Keycloak, **roles** are named permissions. **Groups** are collections of users. A group can be assigned roles — so any user added to a group automatically inherits its roles. Roles appear in the JWT under `realm_access.roles`.

The API already reads `realm_access.roles` from the JWT. The `locker_permissions` table stores a `role_name` string — this is what connects Keycloak roles to locker access rules. This design is already sound.

**Assignment flow:**

```plain
Admin assigns user → Group "Woodshop Team"
                         ↓ (group has role)
                     Realm Role "woodshop-member"
                         ↓ (appears in JWT)
                     locker_permissions WHERE role_name = "woodshop-member"
                         ↓
                     Permission set for that locker
```

### Clients to create

| Client ID             | Type                           | Used by           | Auth flow                 |
| --------------------- | ------------------------------ | ----------------- | ------------------------- |
| `smartlock-api`       | Confidential + service account | FastAPI backend   | Client Credentials        |
| `smartlock-lockers`   | Confidential + service account | All Raspberry Pis | Client Credentials        |
| `smartlock-dashboard` | Public (no secret)             | Svelte SPA        | Authorization Code + PKCE |

### `smartlock-api` service account permissions

Needs read+write access to Keycloak's Admin REST API so that the dashboard can manage users without ever exposing Keycloak admin credentials to the browser. In the Keycloak admin console, go to this client → Service Account Roles → assign from `realm-management`:

- `view-users` — search users by attribute
- `query-users` — required alongside view-users
- `manage-users` — create, update, delete users; set attributes; assign groups
- `view-realm` — read realm configuration
- `query-groups` — list groups

> **Security note:** `manage-users` is a powerful permission. The API must gate all user-management endpoints behind `require_admin()` so only authenticated dashboard admins can trigger these Keycloak calls. The service account secret never leaves the server.

### Realm roles to create

| Role                 | Who gets it            | Purpose                                             |
| -------------------- | ---------------------- | --------------------------------------------------- |
| `admin`              | Fablab managers        | Full dashboard access, all API management endpoints |
| `member`             | All registered members | Base role, no locker access by default              |
| `woodshop-member`    | Woodshop team          | Locker access defined in `locker_permissions`       |
| `electronics-member` | Electronics team       | Same pattern                                        |
| _(add as needed)_    |                        |                                                     |

### Groups to create (optional but recommended)

Groups make bulk assignment easy. A user added to a group gets all the group's roles automatically.

| Group              | Assigned roles                 |
| ------------------ | ------------------------------ |
| `Admins`           | `admin`, `member`              |
| `Members`          | `member`                       |
| `Woodshop Team`    | `member`, `woodshop-member`    |
| `Electronics Team` | `member`, `electronics-member` |

### Custom user attribute: `card_id`

In the Keycloak admin console:

- Realm settings → User Profile → Add attribute `card_id` (string, not required)
- **Important:** Mark it as searchable (`q` parameter in Admin API queries)

---

## NFC Auth Flow (Locker Path)

```plain
1. User taps NFC card
   └─ RPi reads card_id (e.g. "04:AB:CD:12:34:56:78")

2. RPi authenticates to Keycloak (once, token cached until expiry)
   └─ POST /realms/fablab/protocol/openid-connect/token
      body: grant_type=client_credentials
            client_id=smartlock-lockers
            client_secret=<secret>
   └─ Response: { access_token, expires_in }

3. RPi calls the API
   └─ POST /auth/locker/{locker_id}/check
      Header: Authorization: Bearer <access_token>
      Body:   { "card_id": "04:AB:CD:12:34:56:78" }

4. API validates the RPi's JWT
   └─ Verifies signature via Keycloak JWKS
   └─ Checks azp == "smartlock-lockers" (same pattern as existing require_nfc_scanner)

5. API's service account queries Keycloak Admin REST API
   └─ GET /admin/realms/fablab/users?q=card_id:04:AB:CD:12:34:56:78
   └─ Returns user object (or empty → 403 "card not registered")

6. API retrieves user's realm roles
   └─ GET /admin/realms/fablab/users/{userId}/role-mappings/realm
   └─ Returns list of roles: ["member", "woodshop-member"]

7. API queries local DB
   └─ SELECT * FROM locker_permissions
      WHERE locker_id = {locker_id}
      AND role_name IN ("member", "woodshop-member")
   └─ Merges permissions (OR logic: if any role grants can_open, user can open)
   └─ Checks valid_until if set

8. API writes audit log entry
   └─ INSERT INTO access_logs (locker_id, card_id, user_id, username, result, ...)

9. API responds
   └─ 200: { "allowed": true, "display_name": "Alice", "permissions": { "can_open": true, ... } }
   └─ 403: { "allowed": false, "reason": "no_permission" | "card_not_registered" | "expired" }

10. RPi acts on the response
    └─ Unlocks door / shows name on display / logs locally
```

### Per-user overrides (hybrid model)

The current `locker_permissions` model only has `role_name`. To support per-user overrides, the table needs an optional `user_id` column (Keycloak UUID). When both a role-based and a user-specific entry exist for the same locker:

- **User-specific entry takes precedence** (can be used to grant access to someone outside the group, or to explicitly deny someone from a group)

Schema change needed:

```sql
ALTER TABLE locker_permissions
  ADD COLUMN user_id VARCHAR NULL,         -- Keycloak user UUID
  ADD COLUMN subject_type VARCHAR DEFAULT 'role';  -- 'role' or 'user'
```

The existing `UniqueConstraint('role_name', 'locker_id')` needs to accommodate this — either relax it or split into two tables.

---

## Dashboard Auth Flow (Svelte)

Standard OIDC Authorization Code + PKCE — no client secret needed in the browser.

```plain
1. User navigates to dashboard
2. Dashboard redirects to Keycloak:
   GET /realms/fablab/protocol/openid-connect/auth
       ?client_id=smartlock-dashboard
       &redirect_uri=https://dashboard.fablab.local/callback
       &response_type=code
       &scope=openid profile email
       &code_challenge=<PKCE>
       &code_challenge_method=S256

3. Keycloak shows login page (username + password + OTP)

4. On success, Keycloak redirects to:
   https://dashboard.fablab.local/callback?code=<auth_code>

5. Dashboard exchanges code for tokens:
   POST /realms/fablab/protocol/openid-connect/token
       code=<auth_code>
       client_id=smartlock-dashboard
       grant_type=authorization_code
       code_verifier=<PKCE verifier>

6. Dashboard receives:
   - access_token (JWT) — sent as Bearer on all API calls
   - id_token       — contains name, email, roles for display
   - refresh_token  — renew session without re-login

7. API validates access_token on each request
   └─ Existing validate_jwt() + require_admin() already handle this
```

### OTP configuration in Keycloak

Realm Settings → Authentication → Required Actions → enable "Configure OTP" as default.
Or: Authentication → Flows → Browser flow → require OTP after password.

---

## Dashboard User Management (via API proxy)

The dashboard never calls Keycloak directly. All user management goes through the FastAPI backend, which uses the `smartlock-api` service account as a proxy. This keeps Keycloak admin credentials server-side only.

```plain
Admin (browser)
    ↓  POST /users  { username, email, card_id, group }
    ↓  Authorization: Bearer <admin JWT>
FastAPI API
    ├─ require_admin() — verifies the caller has the 'admin' realm role
    └─ Calls Keycloak Admin REST API with smartlock-api service account token:
           POST /admin/realms/fablab/users          → create user
           PUT  /admin/realms/fablab/users/{id}     → set card_id attribute
           PUT  /admin/realms/fablab/users/{id}/groups/{groupId}  → assign group
```

### Dashboard user management actions

| Dashboard action | API endpoint (new) | Keycloak Admin call |
|---|---|---|
| List all members | `GET /users` | `GET /admin/realms/fablab/users` |
| Create a new member | `POST /users` | `POST /admin/realms/fablab/users` |
| Link NFC card to user | `PATCH /users/{id}/card` | `PUT /admin/realms/fablab/users/{id}` (set `card_id` attribute) |
| Assign user to group | `PUT /users/{id}/groups/{groupId}` | `PUT /admin/realms/fablab/users/{id}/groups/{groupId}` |
| Remove user from group | `DELETE /users/{id}/groups/{groupId}` | `DELETE /admin/realms/fablab/users/{id}/groups/{groupId}` |
| List available groups | `GET /groups` | `GET /admin/realms/fablab/groups` |

All of the above endpoints require the `admin` realm role (enforced by `require_admin()`).

### What stays in the Keycloak admin console (one-time setup)

Groups and roles themselves are created once by a human admin at setup time. The dashboard only performs day-to-day operations (members in, members out, card assignment) — it does not create new roles or groups.

---

## Access Control Summary

```plain
locker_permissions table
┌─────────────┬──────────────────────┬──────────┬──────────┬──────────┬──────────┬────────────┐
│  locker_id  │  role_name / user_id │ can_view │ can_open │ can_edit │ can_take │ valid_until│
├─────────────┼──────────────────────┼──────────┼──────────┼──────────┼──────────┼────────────┤
│      1      │ woodshop-member      │   true   │   true   │  false   │   true   │    null    │
│      1      │ admin                │   true   │   true   │   true   │   true   │    null    │
│      2      │ electronics-member   │   true   │   true   │  false   │   true   │    null    │
│      1      │ user:<uuid>          │   true   │   false  │  false   │  false   │ 2026-06-01 │
└─────────────┴──────────────────────┴──────────┴──────────┴──────────┴──────────┴────────────┘
                                                  ↑ example: user explicitly view-only until June
```

Permission resolution:

1. Collect all role-based permissions for this locker that match user's roles
2. Check if a user-specific entry exists → if yes, it overrides (replaces) role permissions
3. Any entry with `valid_until < today` is ignored

---

## Audit Log (new table needed)

```sql
CREATE TABLE access_logs (
    id          SERIAL PRIMARY KEY,
    locker_id   INTEGER REFERENCES lockers(id),
    card_id     VARCHAR NOT NULL,
    user_id     VARCHAR,          -- Keycloak UUID, null if card not registered
    username    VARCHAR,          -- display name, for readability
    result      VARCHAR NOT NULL, -- 'allowed' | 'denied'
    reason      VARCHAR,          -- 'no_permission' | 'card_not_registered' | 'expired' | null
    can_open    BOOLEAN,          -- which permissions were granted (snapshot)
    can_view    BOOLEAN,
    timestamp   TIMESTAMP NOT NULL DEFAULT NOW()
);
```

---

## What Needs to Be Built / Changed

### 1. Keycloak configuration (manual steps)

- Create realm `fablab`
- Create 3 clients (`smartlock-api`, `smartlock-lockers`, `smartlock-dashboard`)
- Create realm roles and groups
- Add `card_id` to user profile
- Configure OTP requirement

### 2. API changes

- New endpoint: `POST /auth/locker/{locker_id}/check`
- New dependency: `require_locker_client()` (checks `azp == "smartlock-lockers"`, same pattern as existing `require_nfc_scanner`)
- New service: `keycloak_admin.py` — calls Keycloak Admin REST API for both read (find user by card_id, get roles) and write (create user, set card_id, assign groups)
- `locker_permissions` schema update: add user_id + subject_type columns (migration needed)
- New `access_logs` table + model + CRUD
- User management endpoints (all protected by `require_admin`): `GET/POST /users`, `PATCH /users/{id}/card`, `PUT/DELETE /users/{id}/groups/{groupId}`, `GET /groups`
- Dashboard endpoints (protected by `require_admin`): manage locker permissions, list audit logs

### 3. Raspberry Pi script

- Client credentials token fetch + caching
- POST card_id to `/auth/locker/{id}/check`
- Act on response (GPIO, display, etc.)

---

## Testing Checklist

### Phase 1 — Keycloak service account

```bash
# 1. Get token for smartlock-api service account
curl -s -X POST \
  https://<keycloak>/realms/fablab/protocol/openid-connect/token \
  -d "grant_type=client_credentials" \
  -d "client_id=smartlock-api" \
  -d "client_secret=<secret>" \
  | jq .access_token

# 2. Search user by card_id
curl -s \
  -H "Authorization: Bearer <token>" \
  https://<keycloak>/admin/realms/fablab/users?q=card_id:TEST123 \
  | jq .

# 3. Get that user's roles
curl -s \
  -H "Authorization: Bearer <token>" \
  https://<keycloak>/admin/realms/fablab/users/<userId>/role-mappings/realm \
  | jq .
```

### Phase 2 — RPi locker auth flow

```bash
# 1. Get token for smartlock-lockers service account
curl -s -X POST \
  https://<keycloak>/realms/fablab/protocol/openid-connect/token \
  -d "grant_type=client_credentials" \
  -d "client_id=smartlock-lockers" \
  -d "client_secret=<secret>" \
  | jq .access_token

# 2. Call the locker check endpoint
curl -s -X POST \
  http://api:8000/auth/locker/1/check \
  -H "Authorization: Bearer <locker_token>" \
  -H "Content-Type: application/json" \
  -d '{"card_id": "TEST123"}' \
  | jq .

# Expected responses:
# { "allowed": true, "display_name": "Alice", "permissions": { "can_open": true, ... } }
# { "allowed": false, "reason": "card_not_registered" }
# { "allowed": false, "reason": "no_permission" }
```

### Phase 3 — Dashboard user management (via API)

```bash
# 1. Get an admin JWT (log in as admin through OIDC, extract access_token)
ADMIN_TOKEN=<access_token from dashboard login>

# 2. Create a new member
curl -s -X POST http://api:8000/users \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"username": "bob", "email": "bob@fablab.local", "card_id": "04:BB:CC:DD:EE:FF"}' \
  | jq .

# 3. List available groups
curl -s http://api:8000/groups \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  | jq .

# 4. Assign user to "Woodshop Team" group
curl -s -X PUT http://api:8000/users/<userId>/groups/<groupId> \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  | jq .

# 5. Confirm that a non-admin JWT gets a 403 on the above endpoints
```

### Phase 4 — Dashboard OIDC

1. Open dashboard in browser → confirm redirect to Keycloak
2. Log in with test admin user → confirm OTP prompt
3. Confirm successful redirect back to dashboard with session
4. Confirm that a non-admin user gets a 403 on admin-only API endpoints

### Phase 5 — End-to-end

1. Use the dashboard API (Phase 3) to create user with `card_id = TEST123` and assign to "Woodshop Team" group
2. Create a locker in the API DB
3. Create a `locker_permission` entry: `role_name = "woodshop-member"`, `can_open = true`
4. Simulate RPi call (Phase 2, step 2) → should return `allowed: true`
5. Remove user from group → repeat → should return `allowed: false, reason: no_permission`
6. Check audit log table for both entries
