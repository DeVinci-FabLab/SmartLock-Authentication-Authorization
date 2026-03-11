# Keycloak Service Account Test Guide

Test that the API can authenticate as a service account and retrieve a user's `card_id` and roles.

**Assumptions:** Keycloak is running and you can reach the admin console. You have an initial admin account.

---

## 1. Create the Realm

1. Log in to the Keycloak admin console (e.g. `https://auth.devinci-fablab.fr` or `http://localhost:8080`)
2. Top-left dropdown → **Create realm**
3. Realm name: `fablab`
4. **Enable** → **Create**

All steps below happen inside the `fablab` realm. Make sure it's selected in the top-left dropdown.

---

## 2. Create Realm Roles

**Left menu → Realm roles → Create role**

Create these two roles (one at a time):

| Role name         | Description                      |
| ----------------- | -------------------------------- |
| `member`          | Base role for all fablab members |
| `woodshop-member` | Access to woodshop lockers       |

Steps for each:

1. Role name → fill in → **Save**
2. No further config needed

---

## 3. Create Groups

**Left menu → Groups → Create group**

| Group name      | Roles to assign             |
| --------------- | --------------------------- |
| `Members`       | `member`                    |
| `Woodshop Team` | `member`, `woodshop-member` |

Steps for each group:

1. Name → fill in → **Create**
2. Click on the group → **Role mapping** tab → **Assign role**
3. Search for the role(s) from the table above → select → **Assign**

---

## 4. Add the `card_id` User Attribute

**Left menu → Realm settings → User profile tab → Create attribute**

- Attribute name: `card_id`
- Display name: `Card ID`
- Leave everything else as default
- **Save**

> This makes `card_id` a proper user profile field that appears in the admin UI and is searchable via the Admin REST API.

---

## 5. Create a Test User

**Left menu → Users → Create new user**

Fill in:

- Username: `alice`
- Email: `alice@fablab.local`
- First name: `Alice`
- **Create**

Then on the user page:

**Set a password:**

- **Credentials** tab → **Set password**
- Password: `test1234` (or anything)
- Temporary: **Off**
- **Save**

**Set the card_id attribute:**

- **Attributes** tab
- Key: `card_id` / Value: `04:AB:CD:12:34:56:78`
- **Save**

**Add to group:**

- **Groups** tab → **Join Group**
- Select `Woodshop Team` → **Join**

---

## 6. Create the `smartlock-api` Client

This is the service account the Python code will use to query Keycloak.

**Left menu → Clients → Create client**

**Step 1 — General settings:**

- Client type: `OpenID Connect`
- Client ID: `smartlock-api`
- **Next**

**Step 2 — Capability config:**

- Client authentication: **On** (makes it confidential)
- Authentication flow: uncheck everything **except** `Service accounts roles`
- **Next → Save**

**Get the client secret:**

- **Credentials** tab → copy the `Client secret` value — you'll need it in the Python script

**Assign Admin API permissions to the service account:**

- **Service account roles** tab → **Assign role**
- Filter by: `Filter by clients` → search `realm-management`
- Select these roles:
  - `query-users`
  - `view-users`
  - `query-groups`
  - `view-realm`
- **Assign**

---

## 7. Python Test Script

Install the only dependency needed:

```bash
pip install httpx
# or: uv add httpx
```

Create `test_keycloak.py`:

```python
import httpx

# ── Config ────────────────────────────────────────────────────────────────────
KEYCLOAK_URL  = "http://localhost:8080"   # change to your Keycloak URL
REALM         = "fablab"
CLIENT_ID     = "smartlock-api"
CLIENT_SECRET = "PASTE_YOUR_SECRET_HERE"  # from step 6

CARD_ID_TO_FIND = "04:AB:CD:12:34:56:78"
# ─────────────────────────────────────────────────────────────────────────────


def get_service_account_token() -> str:
    """Authenticate as the smartlock-api service account (client credentials flow)."""
    url = f"{KEYCLOAK_URL}/realms/{REALM}/protocol/openid-connect/token"
    resp = httpx.post(url, data={
        "grant_type":    "client_credentials",
        "client_id":     CLIENT_ID,
        "client_secret": CLIENT_SECRET,
    })
    resp.raise_for_status()
    token = resp.json()["access_token"]
    print(f"[1] Got service account token (first 40 chars): {token[:40]}...")
    return token


def find_user_by_card_id(token: str, card_id: str) -> dict | None:
    """Search Keycloak users by the card_id custom attribute."""
    url = f"{KEYCLOAK_URL}/admin/realms/{REALM}/users"
    resp = httpx.get(url, params={"q": f"card_id:{card_id}"}, headers={
        "Authorization": f"Bearer {token}"
    })
    resp.raise_for_status()
    users = resp.json()

    if not users:
        print(f"[2] No user found with card_id={card_id}")
        return None

    user = users[0]
    print(f"[2] Found user: id={user['id']}  username={user['username']}")
    print(f"    card_id attribute: {user.get('attributes', {}).get('card_id')}")
    return user


def get_user_realm_roles(token: str, user_id: str) -> list[str]:
    """Retrieve the realm roles assigned to a user (directly + via groups)."""
    url = f"{KEYCLOAK_URL}/admin/realms/{REALM}/users/{user_id}/role-mappings/realm"
    resp = httpx.get(url, headers={"Authorization": f"Bearer {token}"})
    resp.raise_for_status()
    roles = [r["name"] for r in resp.json()]
    print(f"[3] Realm roles: {roles}")
    return roles


def get_user_groups(token: str, user_id: str) -> list[dict]:
    """Retrieve the groups a user belongs to."""
    url = f"{KEYCLOAK_URL}/admin/realms/{REALM}/users/{user_id}/groups"
    resp = httpx.get(url, headers={"Authorization": f"Bearer {token}"})
    resp.raise_for_status()
    groups = resp.json()
    print(f"[4] Groups: {[g['name'] for g in groups]}")
    return groups


if __name__ == "__main__":
    print(f"\nLooking up card_id: {CARD_ID_TO_FIND}\n")

    token = get_service_account_token()
    user  = find_user_by_card_id(token, CARD_ID_TO_FIND)

    if user is None:
        print("\nResult: card not registered — access denied")
    else:
        roles  = get_user_realm_roles(token, user["id"])
        groups = get_user_groups(token, user["id"])

        print(f"\n── Result ──────────────────────────────")
        print(f"  User:   {user['firstName']} {user['lastName']} ({user['username']})")
        print(f"  Roles:  {roles}")
        print(f"  Groups: {[g['name'] for g in groups]}")

        # Simulate a permission check against locker_permissions table logic
        locker_permissions = {
            "woodshop-member": {"can_open": True,  "can_view": True, "can_take": True},
            "member":          {"can_open": False, "can_view": True, "can_take": False},
        }
        merged = {"can_open": False, "can_view": False, "can_take": False}
        for role in roles:
            if role in locker_permissions:
                for perm, val in locker_permissions[role].items():
                    merged[perm] = merged[perm] or val

        print(f"  Permissions (simulated for locker 1): {merged}")
```

Run it:

```bash
python test_keycloak.py
```

**Expected output:**

```
Looking up card_id: 04:AB:CD:12:34:56:78

[1] Got service account token (first 40 chars): eyJhbGciOiJSUzI1NiIsInR5cCIgOi...
[2] Found user: id=<uuid>  username=alice
    card_id attribute: ['04:AB:CD:12:34:56:78']
[3] Realm roles: ['default-roles-fablab', 'member', 'woodshop-member']
[4] Groups: ['Woodshop Team']

── Result ──────────────────────────────
  User:   Alice  (alice)
  Roles:  ['default-roles-fablab', 'member', 'woodshop-member']
  Groups: ['Woodshop Team']
  Permissions (simulated for locker 1): {'can_open': True, 'can_view': True, 'can_take': True}
```

---

## 8. Common Errors

| Error                                      | Cause                                               | Fix                                                       |
| ------------------------------------------ | --------------------------------------------------- | --------------------------------------------------------- |
| `401 Unauthorized` on token request        | Wrong `CLIENT_SECRET`                               | Re-copy from Clients → smartlock-api → Credentials tab    |
| `403 Forbidden` on Admin API call          | Service account missing roles                       | Re-check step 6 — Service account roles tab               |
| Empty `[]` on user search                  | `card_id` attribute not searchable                  | Re-check step 4 — attribute must be saved in User Profile |
| Empty `[]` on user search                  | Value has whitespace or wrong case                  | Copy the exact string set in step 5                       |
| `400 Bad Request` on token                 | `Service accounts roles` not enabled on client      | Re-check step 6 capability config                         |
| Roles list only has `default-roles-fablab` | User not in a group, or group has no roles assigned | Re-check steps 3 and 5                                    |
