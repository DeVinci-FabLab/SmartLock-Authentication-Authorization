# SmartLock API Reference

Base URL: `http://<host>:8000`

Interactive docs (Swagger UI): `http://<host>:8000/docs`

---

## Authentication

All endpoints require a Bearer JWT issued by Keycloak. Include the token in the `Authorization` header:

```
Authorization: Bearer <access_token>
```

There are three types of tokens used by the system:

| Client | Grant type | Who uses it | Access level |
|---|---|---|---|
| `smartlock-dashboard` | `password` | Admin users (dashboard frontend) | Full CRUD + user management (read) |
| `smartlock-lockers` | `client_credentials` | Raspberry Pi terminals | `POST /auth/locker/{id}/check` only |
| `nfc-scanner` | `client_credentials` | NFC scanner module | `POST /badge/scan` only |

### Obtain an admin token (password grant)

```bash
curl -X POST "${KEYCLOAK_URL}/realms/${REALM}/protocol/openid-connect/token" \
  -d "grant_type=password" \
  -d "client_id=smartlock-dashboard" \
  -d "username=${USERNAME}" \
  -d "password=${PASSWORD}"
```

### Obtain a service account token (client_credentials)

```bash
curl -X POST "${KEYCLOAK_URL}/realms/${REALM}/protocol/openid-connect/token" \
  -d "grant_type=client_credentials" \
  -d "client_id=smartlock-lockers" \
  -d "client_secret=${LOCKER_CLIENT_SECRET}"
```

---

## Error format

All errors follow this structure:

```json
{
  "detail": "Human-readable error message"
}
```

Common HTTP status codes:
- `401` — Missing or invalid token
- `403` — Insufficient permissions (wrong role or wrong client)
- `404` — Resource not found
- `409` — Conflict (duplicate resource)
- `500` — Internal server error

---

## Endpoints

### Categories

| Method | Path | Auth | Description |
|---|---|---|---|
| `GET` | `/categories/` | Any valid JWT | List categories |
| `GET` | `/categories/{id}` | Any valid JWT | Get category by ID |
| `POST` | `/categories/` | Admin | Create category |
| `PUT` | `/categories/{id}` | Admin | Update category |
| `DELETE` | `/categories/{id}` | Admin | Delete category |

**Create / Update body:**

```json
{
  "name": "Outillage"       // required on create, 1-100 chars
}
```

**Response:**

```json
{
  "id": 1,
  "name": "Outillage",
  "created_at": "2025-01-15T10:30:00Z",
  "updated_at": "2025-01-15T10:30:00Z"
}
```

---

### Items

| Method | Path | Auth | Description |
|---|---|---|---|
| `GET` | `/items/?skip=0&limit=100` | Any valid JWT | List items |
| `GET` | `/items/{id}` | Any valid JWT | Get item by ID |
| `POST` | `/items/` | Admin | Create item |
| `PUT` | `/items/{id}` | Admin | Update item |
| `DELETE` | `/items/{id}` | Admin | Delete item |

**Create body:**

```json
{
  "name": "Perceuse",          // required, 1-255 chars
  "reference": "P-01",         // required, 1-50 chars
  "description": "optional",   // optional
  "category_id": 1             // required, must exist
}
```

**Update body:** All fields optional.

**Response:**

```json
{
  "id": 1,
  "name": "Perceuse",
  "reference": "P-01",
  "description": null,
  "category_id": 1,
  "created_at": "2025-01-15T10:30:00Z",
  "updated_at": "2025-01-15T10:30:00Z"
}
```

---

### Lockers

| Method | Path | Auth | Description |
|---|---|---|---|
| `GET` | `/lockers/?skip=0&limit=100` | Any valid JWT | List lockers |
| `GET` | `/lockers/{id}` | Any valid JWT | Get locker by ID |
| `GET` | `/lockers/{id}/stock` | Any valid JWT | Get stock in a locker |
| `POST` | `/lockers/` | Admin | Create locker |
| `PUT` | `/lockers/{id}` | Admin | Update locker |
| `DELETE` | `/lockers/{id}` | Admin | Delete locker (cascades stock, permissions, logs) |

**Create body:**

```json
{
  "locker_type": "standard",  // required, 1-50 chars
  "is_active": true            // optional, default true
}
```

**Update body:** All fields optional.

**Response:**

```json
{
  "id": 1,
  "locker_type": "standard",
  "is_active": true,
  "created_at": "2025-01-15T10:30:00Z",
  "updated_at": "2025-01-15T10:30:00Z"
}
```

---

### Stock

| Method | Path | Auth | Description |
|---|---|---|---|
| `GET` | `/stock/?skip=0&limit=100` | Any valid JWT | List all stock entries |
| `GET` | `/stock/{id}` | Any valid JWT | Get stock entry by ID |
| `POST` | `/stock/` | Admin | Create stock entry |
| `PUT` | `/stock/{id}` | Admin | Update stock entry |
| `DELETE` | `/stock/{id}` | Admin | Delete stock entry |

A stock entry links one item to one locker with a quantity. The pair `(item_id, locker_id)` must be unique.

**Create body:**

```json
{
  "item_id": 1,              // required, must exist
  "locker_id": 1,            // required, must exist
  "quantity": 10,            // optional, default 0, >= 0
  "unit_measure": "units"    // optional, default "units"
}
```

**Update body:** All fields optional.

**Response:**

```json
{
  "id": 1,
  "item_id": 1,
  "locker_id": 1,
  "quantity": 10,
  "unit_measure": "units",
  "created_at": "2025-01-15T10:30:00Z",
  "updated_at": "2025-01-15T10:30:00Z"
}
```

---

### Locker Permissions

All permission endpoints require **Admin** auth.

| Method | Path | Auth | Description |
|---|---|---|---|
| `GET` | `/lockers/{locker_id}/permissions` | Admin | List permissions for a locker |
| `POST` | `/lockers/{locker_id}/permissions` | Admin | Create permission |
| `PUT` | `/lockers/permissions/{permission_id}` | Admin | Update permission |
| `DELETE` | `/lockers/permissions/{permission_id}` | Admin | Delete permission |

Permissions can target either a **role** (all users with that Keycloak role) or a specific **user** (by Keycloak user UUID). User-specific permissions override role-based permissions.

**Create body:**

```json
{
  "locker_id": 1,               // required, must match URL
  "subject_type": "role",       // "role" or "user"
  "role_name": "3D",            // required if subject_type is "role"
  "user_id": null,              // required if subject_type is "user" (Keycloak UUID)
  "can_view": true,             // default true
  "can_open": true,             // default false
  "can_edit": false,            // default false
  "can_take": false,            // default false
  "can_manage": false,          // default false
  "valid_until": "2025-12-31T23:59:59"  // optional, ISO 8601
}
```

**Response:**

```json
{
  "id": 1,
  "locker_id": 1,
  "subject_type": "role",
  "role_name": "3D",
  "user_id": null,
  "can_view": true,
  "can_open": true,
  "can_edit": false,
  "can_take": false,
  "can_manage": false,
  "valid_until": null,
  "created_at": "2025-01-15T10:30:00Z"
}
```

---

### Badge (NFC)

| Method | Path | Auth | Description |
|---|---|---|---|
| `POST` | `/badge/scan` | NFC Scanner (`nfc-scanner`) | Register a scanned NFC badge |
| `GET` | `/badge/pending` | Admin | List pending (unassigned) badges |
| `PATCH` | `/badge/{card_id}/assign` | Admin | Mark a badge as assigned |

**Scan body:**

```json
{
  "card_id": "AA:BB:CC:11:22"  // required, 1-64 chars
}
```

**Scan response (201):**

```json
{
  "success": true,
  "message": "Carte enregistree, en attente d'assignation par un admin",
  "card_id": "AA:BB:CC:11:22"
}
```

**Pending response:**

```json
[
  {
    "id": 1,
    "card_id": "AA:BB:CC:11:22",
    "scanned_at": "2025-01-15T10:30:00Z",
    "status": "pending"
  }
]
```

---

### Locker Access Check (Hardware)

| Method | Path | Auth | Description |
|---|---|---|---|
| `POST` | `/auth/locker/{locker_id}/check` | Locker client (`smartlock-lockers`) | Check if a badge can open a locker |

**Request body:**

```json
{
  "card_id": "AA:BB:CC:11:22"
}
```

**Response:**

```json
{
  "allowed": true,
  "display_name": "Alice Dupont",
  "reason": null,
  "permissions": {
    "can_view": true,
    "can_open": true,
    "can_edit": false,
    "can_take": false,
    "can_manage": false
  }
}
```

When denied:

```json
{
  "allowed": false,
  "display_name": "Alice Dupont",
  "reason": "no_permission",
  "permissions": null
}
```

Possible `reason` values: `card_not_registered`, `keycloak_error`, `no_permission`.

---

### Audit Logs

All log endpoints require **Admin** auth.

| Method | Path | Auth | Description |
|---|---|---|---|
| `GET` | `/logs/?skip=0&limit=100&locker_id=1` | Admin | List access logs (optional locker filter) |

**Response:**

```json
[
  {
    "id": 1,
    "locker_id": 1,
    "card_id": "AA:BB:CC:11:22",
    "user_id": "keycloak-uuid",
    "username": "Alice Dupont",
    "result": "allowed",
    "reason": null,
    "can_open": true,
    "can_view": true,
    "timestamp": "2025-01-15T10:30:00Z"
  }
]
```

---

### User Management (Keycloak - Read Only)

All user endpoints require **Admin** auth. User/group creation and modification is done exclusively via the Keycloak admin interface.

| Method | Path | Auth | Description |
|---|---|---|---|
| `GET` | `/users?search=&first=0&max_results=100` | Admin | List Keycloak users |
| `GET` | `/groups` | Admin | List Keycloak groups |
