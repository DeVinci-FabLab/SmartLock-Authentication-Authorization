import os
import httpx
from dotenv import load_dotenv

load_dotenv()

# ── Config ────────────────────────────────────────────────────────────────────
KEYCLOAK_URL  = os.environ["KEYCLOAK_URL"]
REALM         = os.environ["KEYCLOAK_REALM"]
CLIENT_ID     = os.environ["KEYCLOAK_CLIENT_ID"]
CLIENT_SECRET = os.environ["KEYCLOAK_CLIENT_SECRET"]

# Two card IDs to test: one registered, one unknown
TEST_CASES = [
    "04:AB:CD:12:34:56:78",  # registered — should find alice
    "FF:FF:FF:FF:FF:FF:FF",  # unknown    — should return None
]
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
    print(f"[1] Token obtenu (40 premiers caractères) : {token[:40]}...")
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
        print(f"[2] Aucun utilisateur trouvé avec card_id={card_id}")
        return None

    user = users[0]
    print(f"[2] Utilisateur trouvé : id={user['id']}  username={user['username']}")
    print(f"    card_id : {user.get('attributes', {}).get('card_id')}")
    return user


def get_user_realm_roles(token: str, user_id: str) -> list[str]:
    """Retrieve effective realm roles (direct + inherited via parent groups)."""
    # /composite returns all effective roles, including those inherited from parent groups.
    # Without /composite, roles assigned to parent groups would be missing.
    url = f"{KEYCLOAK_URL}/admin/realms/{REALM}/users/{user_id}/role-mappings/realm/composite"
    resp = httpx.get(url, headers={"Authorization": f"Bearer {token}"})
    resp.raise_for_status()
    roles = [r["name"] for r in resp.json()]
    print(f"[3] Rôles effectifs : {roles}")
    return roles


def get_user_groups(token: str, user_id: str) -> list[dict]:
    """Retrieve the groups a user belongs to."""
    url = f"{KEYCLOAK_URL}/admin/realms/{REALM}/users/{user_id}/groups"
    resp = httpx.get(url, headers={"Authorization": f"Bearer {token}"})
    resp.raise_for_status()
    groups = resp.json()
    print(f"[4] Groupes : {[g['name'] for g in groups]}")
    return groups


def check_card(token: str, card_id: str) -> None:
    print(f"\n{'─' * 50}")
    print(f"Recherche du card_id : {card_id}")
    print(f"{'─' * 50}")

    user = find_user_by_card_id(token, card_id)

    if user is None:
        print("Résultat : carte non enregistrée — accès refusé")
        return

    roles  = get_user_realm_roles(token, user["id"])
    groups = get_user_groups(token, user["id"])

    print(f"\n── Résultat ────────────────────────────")
    print(f"  Utilisateur : {user.get('firstName', '')} {user.get('lastName', '')} ({user['username']})")
    print(f"  Rôles       : {roles}")
    print(f"  Groupes     : {[g['name'] for g in groups]}")

    # Simulate permission check against locker_permissions table logic
    locker_permissions = {
        "membre-atelier": {"can_open": True,  "can_view": True, "can_take": True},
        "membre":         {"can_open": False, "can_view": True, "can_take": False},
    }
    merged = {"can_open": False, "can_view": False, "can_take": False}
    for role in roles:
        if role in locker_permissions:
            for perm, val in locker_permissions[role].items():
                merged[perm] = merged[perm] or val

    print(f"  Permissions (simulation casier 1) : {merged}")


if __name__ == "__main__":
    token = get_service_account_token()
    for card_id in TEST_CASES:
        check_card(token, card_id)
