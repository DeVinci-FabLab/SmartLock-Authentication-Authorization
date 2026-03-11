# API Migration — Gap Analysis & Implementation Plan

What needs to be built or changed for the system design to work end-to-end.
Reference: `docs/system-design.md`.

---

## Current State

| Area | Status |
|---|---|
| JWT validation (`validate_jwt`, `require_admin`, `require_nfc_scanner`) | Done |
| NFC card scan/assign workflow (`/badge/*`) | Done |
| CRUD for lockers, items, stock, categories | Done |
| `locker_permissions` DB model | Done (structure only) |
| `locker_permissions` CRUD + routes | Empty stub |
| Locker auth check endpoint | Missing |
| Keycloak Admin REST API integration | Missing |
| Audit log | Missing |
| Auth guards on standard CRUD routes | Missing |
| User management endpoints (dashboard) | Missing |

---

## Implementation Steps

### 1. `src/core/keycloak_admin.py` + config

**Depends on:** nothing — do this first, everything else calls it.

New module that holds all calls to the Keycloak Admin REST API using the `smartlock-api` service account (client credentials flow).

Functions to implement:

```python
async def get_admin_token() -> str
    # POST /realms/{realm}/protocol/openid-connect/token
    # grant_type=client_credentials, client_id, client_secret
    # Returns access_token — consider caching until exp

async def find_user_by_card_id(card_id: str) -> dict | None
    # GET /admin/realms/{realm}/users?q=card_id:{card_id}
    # Returns first match or None

async def get_user_effective_roles(user_id: str) -> list[str]
    # GET /admin/realms/{realm}/users/{user_id}/role-mappings/realm/composite
    # Returns role name list — use /composite to include parent group roles

async def get_user_groups(user_id: str) -> list[dict]
    # GET /admin/realms/{realm}/users/{user_id}/groups

async def create_user(username, email, first_name, last_name) -> str
    # POST /admin/realms/{realm}/users
    # Returns new user UUID

async def set_user_card_id(user_id: str, card_id: str) -> None
    # PUT /admin/realms/{realm}/users/{user_id}
    # Body: { "attributes": { "card_id": [card_id] } }

async def assign_user_to_group(user_id: str, group_id: str) -> None
    # PUT /admin/realms/{realm}/users/{user_id}/groups/{group_id}

async def remove_user_from_group(user_id: str, group_id: str) -> None
    # DELETE /admin/realms/{realm}/users/{user_id}/groups/{group_id}

async def list_groups() -> list[dict]
    # GET /admin/realms/{realm}/groups
```

**Config change required** — add to `src/core/config.py`:

```python
KEYCLOAK_CLIENT_ID: str = "smartlock-api"
KEYCLOAK_CLIENT_SECRET: str  # no default — must be set in .env
```

---

### 2. `POST /auth/locker/{locker_id}/check`

**Depends on:** step 1, locker_permissions CRUD (step 3).

New router `src/routes/auth.py`. This is the endpoint the Raspberry Pi calls on every card scan.

New dependency in `src/core/keycloak.py`:

```python
async def require_locker_client(payload: dict = Depends(validate_jwt)) -> dict:
    # Same pattern as require_nfc_scanner()
    # Checks azp == "smartlock-lockers"
```

Endpoint logic:

```python
POST /auth/locker/{locker_id}/check
Auth: require_locker_client()
Body: { "card_id": str }

1. find_user_by_card_id(card_id)          → 403 "card_not_registered" if None
2. get_user_effective_roles(user_id)
3. query locker_permissions WHERE locker_id = X
     AND (role_name IN roles OR user_id = user_id)
4. merge permissions (OR logic across role rows)
   user-specific row overrides role rows if present
5. check valid_until — ignore expired rows
6. write access_logs row
7. return { allowed, display_name, permissions: {can_open, can_view, ...} }
   or 403 { allowed: false, reason: "no_permission" | "card_not_registered" | "expired" }
```

---

### 3. `locker_permissions` CRUD + routes

**Depends on:** nothing — model already exists.

Fill in `src/crud/crud_locker_permission.py`:

```python
get_permissions_for_locker(db, locker_id) -> list[Locker_Permission]
get_permission(db, permission_id) -> Locker_Permission | None
create_permission(db, locker_id, role_name, can_view, can_open, ...) -> Locker_Permission
update_permission(db, permission_id, **fields) -> Locker_Permission
delete_permission(db, permission_id) -> None
```

New router `src/routes/locker_permissions.py`:

```
GET    /lockers/{locker_id}/permissions        require_admin
POST   /lockers/{locker_id}/permissions        require_admin
PUT    /lockers/{locker_id}/permissions/{id}   require_admin
DELETE /lockers/{locker_id}/permissions/{id}   require_admin
```

---

### 4. `locker_permissions` model migration

**Depends on:** step 3.

The current model only supports role-based permissions. For per-user overrides (hybrid model) add two columns:

```python
user_id      = Column(String, nullable=True)   # Keycloak UUID
subject_type = Column(String, default="role")  # "role" or "user"
```

Permission resolution rule: if a `subject_type="user"` row exists for this locker+user, it takes full precedence over any role-based rows.

The existing `UniqueConstraint('role_name', 'locker_id')` needs to be replaced — a user-specific row has no `role_name`. Options:
- Partial unique index: unique on `(role_name, locker_id)` WHERE `subject_type = 'role'`
- Or split into two tables: `role_permissions` and `user_permission_overrides`

Generate migration after model changes:

```bash
uv run alembic revision --autogenerate -m "add user_id and subject_type to locker_permissions"
uv run alembic upgrade head
```

---

### 5. Audit log

**Depends on:** nothing — standalone.

New model `src/models/access_log.py`:

```python
class AccessLog(Base):
    __tablename__ = "access_logs"

    id         = Column(Integer, primary_key=True)
    locker_id  = Column(Integer, ForeignKey("lockers.id"), nullable=True)
    card_id    = Column(String, nullable=False)
    user_id    = Column(String, nullable=True)   # None if card not registered
    username   = Column(String, nullable=True)
    result     = Column(String, nullable=False)  # "allowed" | "denied"
    reason     = Column(String, nullable=True)   # "no_permission" | "card_not_registered" | "expired"
    can_open   = Column(Boolean, nullable=True)  # snapshot of granted permissions
    can_view   = Column(Boolean, nullable=True)
    timestamp  = Column(DateTime, default=datetime.utcnow, nullable=False)
```

New CRUD `src/crud/crud_access_log.py`:

```python
create_log(db, locker_id, card_id, user_id, username, result, reason, permissions) -> AccessLog
get_logs(db, locker_id=None, skip=0, limit=100) -> list[AccessLog]
```

Expose via dashboard endpoint:

```
GET /lockers/{locker_id}/logs   require_admin
GET /logs                       require_admin   (global view)
```

Generate migration:

```bash
uv run alembic revision --autogenerate -m "add access_logs table"
uv run alembic upgrade head
```

---

### 6. Auth guards on existing CRUD routes

**Depends on:** nothing — existing routes only.

Current state: all `/lockers`, `/items`, `/stock`, `/categories` endpoints have zero authentication.

Changes per route file:

| Endpoint type | Dependency to add |
|---|---|
| All `GET` endpoints | `validate_jwt` (any authenticated user) |
| `POST`, `PUT`, `DELETE` | `require_admin` |

Pattern to follow (already used in `badge.py`):

```python
@router.post("/", dependencies=[Depends(require_admin)])
@router.get("/", dependencies=[Depends(validate_jwt)])
```

---

### 7. User management endpoints

**Depends on:** step 1 (`keycloak_admin.py`).

New router `src/routes/users.py`. All endpoints require `require_admin`.
These proxy directly to the Keycloak Admin REST API — no local DB writes.

```
GET    /users                            list members
POST   /users                            create member (username, email, first_name, last_name)
PATCH  /users/{user_id}/card             set card_id attribute
PUT    /users/{user_id}/groups/{group_id} assign to group
DELETE /users/{user_id}/groups/{group_id} remove from group
GET    /groups                           list available groups
```

---

## Summary Table

| Step | File(s) | Type | Effort |
|---|---|---|---|
| 1 | `src/core/keycloak_admin.py`, `src/core/config.py` | New module + config | Medium |
| 2 | `src/routes/auth.py`, `src/core/keycloak.py` | New route + dependency | Medium |
| 3 | `src/crud/crud_locker_permission.py`, `src/routes/locker_permissions.py` | Fill stub + new route | Small |
| 4 | `src/models/locker_permission.py` + migration | Model change | Small |
| 5 | `src/models/access_log.py`, `src/crud/crud_access_log.py`, route addition | New table + CRUD | Small |
| 6 | All existing route files | Auth guards | Small |
| 7 | `src/routes/users.py` | New route | Medium |
