import os
import time

import requests
from dotenv import load_dotenv

load_dotenv()

API_URL = "http://localhost:8000"
KEYCLOAK_URL = os.getenv(
    "KEYCLOAK_URL", "https://auth.devinci-fablab.fr"
)
REALM = os.getenv("KEYCLOAK_REALM", "master")

ADMIN_USERNAME = os.getenv("ADMIN_USERNAME", "florian_c")
ADMIN_PASSWORD = os.getenv(
    "ADMIN_PASSWORD", "votre_mot_de_passe"
)
LOCKER_CLIENT_SECRET = os.getenv(
    "LOCKER_CLIENT_SECRET", "secret_rpi"
)
NFC_CLIENT_SECRET = os.getenv(
    "NFC_CLIENT_SECRET", "secret_nfc"
)

# Variables globales pour garder la trace des IDs créés
TEST_DATA = {}
UNIQUE_ID = int(time.time())

print("==================================================")
print("DEMARRAGE DE LA SUITE DE TESTS API")
print("==================================================\n")

# =================================================================
# 1. AUTHENTIFICATION & SÉCURITÉ
# =================================================================
print("1. AUTHENTIFICATION & TOKENS")
token_url = (
    f"{KEYCLOAK_URL}/realms/{REALM}"
    "/protocol/openid-connect/token"
)

# Admin Token
resp = requests.post(
    token_url,
    data={
        "grant_type": "password",
        "client_id": "smartlock-dashboard",
        "username": ADMIN_USERNAME,
        "password": ADMIN_PASSWORD,
    },
)
assert resp.status_code == 200, "Echec Token Admin"
headers_admin = {
    "Authorization": f"Bearer {resp.json()['access_token']}"
}
print("  Token Admin obtenu")

# RPI Token
resp = requests.post(
    token_url,
    data={
        "grant_type": "client_credentials",
        "client_id": "smartlock-lockers",
        "client_secret": LOCKER_CLIENT_SECRET,
    },
)
assert resp.status_code == 200, "Echec Token RPI"
headers_rpi = {
    "Authorization": f"Bearer {resp.json()['access_token']}"
}
print("  Token Raspberry Pi obtenu")

# NFC Token
resp = requests.post(
    token_url,
    data={
        "grant_type": "client_credentials",
        "client_id": "nfc-scanner",
        "client_secret": NFC_CLIENT_SECRET,
    },
)
assert resp.status_code == 200, (
    f"Echec Token NFC: {resp.text}"
)
headers_nfc = {
    "Authorization": f"Bearer {resp.json()['access_token']}"
}
print("  Token NFC Scanner obtenu")

print("\n2. TESTS DE SECURITE (SANS TOKEN)")
resp = requests.get(f"{API_URL}/lockers/")
assert resp.status_code in [401, 403], (
    f"Fail Security: {resp.status_code}"
)
print("  Acces anonyme bloque sur /lockers/ (401/403)")

# =================================================================
# 3. CATÉGORIES (CRUD)
# =================================================================
print("\n3. TESTS CATEGORIES (/categories)")
resp = requests.post(
    f"{API_URL}/categories/",
    headers=headers_admin,
    json={"name": f"Cat-{UNIQUE_ID}"},
)
assert resp.status_code in [200, 201], (
    f"Erreur: {resp.text}"
)
TEST_DATA["cat_id"] = resp.json()["id"]
print(f"  POST /categories/ (ID: {TEST_DATA['cat_id']})")

resp = requests.get(
    f"{API_URL}/categories/{TEST_DATA['cat_id']}",
    headers=headers_admin,
)
assert resp.status_code == 200
print("  GET /categories/{id}")

resp = requests.get(
    f"{API_URL}/categories/999999", headers=headers_admin
)
assert resp.status_code == 404
print("  GET /categories/999999 (404 Not Found)")

# =================================================================
# 4. ITEMS (CRUD)
# =================================================================
print("\n4. TESTS ITEMS (/items)")
resp = requests.post(
    f"{API_URL}/items/",
    headers=headers_admin,
    json={
        "name": f"Item-{UNIQUE_ID}",
        "reference": f"REF-{UNIQUE_ID}",
        "category_id": TEST_DATA["cat_id"],
    },
)
assert resp.status_code in [200, 201], (
    f"Erreur: {resp.text}"
)
TEST_DATA["item_id"] = resp.json()["id"]
print(f"  POST /items/ (ID: {TEST_DATA['item_id']})")

resp = requests.get(
    f"{API_URL}/items/", headers=headers_admin
)
assert resp.status_code == 200
print("  GET /items/")

# =================================================================
# 5. CASIERS (CRUD)
# =================================================================
print("\n5. TESTS CASIERS (/lockers)")
resp = requests.post(
    f"{API_URL}/lockers/",
    headers=headers_admin,
    json={
        "locker_type": "standard",
    },
)
assert resp.status_code in [200, 201], (
    f"Erreur: {resp.text}"
)
TEST_DATA["locker_id"] = resp.json()["id"]
print(
    f"  POST /lockers/ (ID: {TEST_DATA['locker_id']})"
)

resp = requests.put(
    f"{API_URL}/lockers/{TEST_DATA['locker_id']}",
    headers=headers_admin,
    json={"is_active": False},
)
assert resp.status_code == 200
print("  PUT /lockers/{id} (Desactivation du casier)")

# =================================================================
# 6. STOCK & PERMISSIONS
# =================================================================
print("\n6. TESTS STOCK & PERMISSIONS")
resp = requests.post(
    f"{API_URL}/stock/",
    headers=headers_admin,
    json={
        "locker_id": TEST_DATA["locker_id"],
        "item_id": TEST_DATA["item_id"],
        "quantity": 10,
    },
)
assert resp.status_code in [200, 201]
TEST_DATA["stock_id"] = resp.json()["id"]
print("  POST /stock/ (Ajout de 10 items)")

resp = requests.get(
    f"{API_URL}/lockers/{TEST_DATA['locker_id']}/stock",
    headers=headers_admin,
)
assert resp.status_code == 200
assert len(resp.json()) > 0
print("  GET /lockers/{id}/stock (Lecture du stock)")

resp = requests.post(
    f"{API_URL}/lockers/{TEST_DATA['locker_id']}/permissions",
    headers=headers_admin,
    json={
        "locker_id": TEST_DATA["locker_id"],
        "subject_type": "role",
        "role_name": "3D",
        "can_open": True,
    },
)
assert resp.status_code in [200, 201]
TEST_DATA["perm_id"] = resp.json()["id"]
print("  POST /lockers/{id}/permissions (Permission 3D)")

# =================================================================
# 7. BADGES & WORKFLOW NFC
# =================================================================
print("\n7. TESTS BADGES & NFC (/badge & /auth)")
test_card = (
    f"AA:BB:CC:"
    f"{str(UNIQUE_ID)[-6:-4]}:"
    f"{str(UNIQUE_ID)[-4:-2]}:"
    f"{str(UNIQUE_ID)[-2:]}"
)

# Machine (Module NFC) scanne un nouveau badge
resp = requests.post(
    f"{API_URL}/badge/scan",
    headers=headers_nfc,
    json={"card_id": test_card},
)
assert resp.status_code in [200, 201, 202], (
    f"Echec scan badge: {resp.status_code} - {resp.text}"
)
print(
    f"  POST /badge/scan (Badge scanne: {test_card})"
)

# Admin liste les badges en attente
resp = requests.get(
    f"{API_URL}/badge/pending", headers=headers_admin
)
assert resp.status_code == 200
print("  GET /badge/pending (Badge en attente)")

# Machine tente d'ouvrir le casier
resp = requests.post(
    f"{API_URL}/auth/locker/{TEST_DATA['locker_id']}/check",
    headers=headers_rpi,
    json={"card_id": test_card},
)
assert resp.status_code == 200
assert not resp.json()["allowed"]
print(
    "  POST /auth/locker/{id}/check"
    " (Ouverture refusee car non assigne)"
)

# =================================================================
# 8. UTILISATEURS & AUDIT LOGS
# =================================================================
print("\n8. TESTS UTILISATEURS & LOGS (/users, /logs)")
resp = requests.get(
    f"{API_URL}/users", headers=headers_admin
)
assert resp.status_code == 200
print("  GET /users (Relais Keycloak OK)")

resp = requests.get(
    f"{API_URL}/logs/?locker_id={TEST_DATA['locker_id']}",
    headers=headers_admin,
)
assert resp.status_code == 200
assert len(resp.json()) > 0
print("  GET /logs/ (Historique d'acces enregistre)")

# =================================================================
# 9. NETTOYAGE COMPLET (CASCADE)
# =================================================================
print("\n9. NETTOYAGE DE LA BASE DE DONNEES")

requests.delete(
    f"{API_URL}/lockers/{TEST_DATA['locker_id']}",
    headers=headers_admin,
)
print(
    f"  DELETE /lockers/{TEST_DATA['locker_id']}"
    " (Supprime Stock, Permissions, Logs)"
)

requests.delete(
    f"{API_URL}/items/{TEST_DATA['item_id']}",
    headers=headers_admin,
)
print(f"  DELETE /items/{TEST_DATA['item_id']}")

requests.delete(
    f"{API_URL}/categories/{TEST_DATA['cat_id']}",
    headers=headers_admin,
)
print(f"  DELETE /categories/{TEST_DATA['cat_id']}")

print("\nTOUTES LES ROUTES FONCTIONNENT (100% SUCCESS) !")
print("==================================================")
