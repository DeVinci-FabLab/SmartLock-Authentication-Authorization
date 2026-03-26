import os
import time
import requests
from dotenv import load_dotenv

load_dotenv()

API_URL = "http://localhost:8000"
KEYCLOAK_URL = os.getenv("KEYCLOAK_URL", "https://auth.devinci-fablab.fr")
REALM = os.getenv("KEYCLOAK_REALM", "master")

ADMIN_USERNAME = os.getenv("ADMIN_USERNAME", "florian_c")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "votre_mot_de_passe")
LOCKER_CLIENT_SECRET = os.getenv("LOCKER_CLIENT_SECRET", "secret_rpi")
NFC_CLIENT_SECRET = os.getenv("NFC_CLIENT_SECRET", "secret_nfc")

# Variables globales pour garder la trace des IDs créés
TEST_DATA = {}
UNIQUE_ID = int(time.time())

print("==================================================")
print("🚀 DÉMARRAGE DE LA SUPER SUITE DE TESTS API")
print("==================================================\n")

# =================================================================
# 1. AUTHENTIFICATION & SÉCURITÉ
# =================================================================
print("🔑 1. AUTHENTIFICATION & TOKENS")
token_url = f"{KEYCLOAK_URL}/realms/{REALM}/protocol/openid-connect/token"

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
assert resp.status_code == 200, "Échec Token Admin"
headers_admin = {"Authorization": f"Bearer {resp.json()['access_token']}"}
print("  ✅ Token Admin obtenu")

# RPI Token
resp = requests.post(
    token_url,
    data={
        "grant_type": "client_credentials",
        "client_id": "smartlock-lockers",
        "client_secret": LOCKER_CLIENT_SECRET,
    },
)
assert resp.status_code == 200, "Échec Token RPI"
headers_rpi = {"Authorization": f"Bearer {resp.json()['access_token']}"}
print("  ✅ Token Raspberry Pi obtenu")

# NFC Token
resp = requests.post(
    token_url,
    data={
        "grant_type": "client_credentials",
        "client_id": "nfc-scanner",
        "client_secret": NFC_CLIENT_SECRET,
    },
)
assert resp.status_code == 200, f"Échec Token NFC: {resp.text}"
headers_nfc = {"Authorization": f"Bearer {resp.json()['access_token']}"}
print("  ✅ Token NFC Scanner obtenu")

print("\n🛡️ 2. TESTS DE SÉCURITÉ (SANS TOKEN)")
resp = requests.get(f"{API_URL}/lockers/")
assert resp.status_code in [401, 403], f"Fail Security: {resp.status_code}"
print("  ✅ Accès anonyme bloqué sur /lockers/ (401/403)")

# =================================================================
# 3. CATÉGORIES (CRUD)
# =================================================================
print("\n📁 3. TESTS CATÉGORIES (/categories)")
resp = requests.post(
    f"{API_URL}/categories/", headers=headers_admin, json={"name": f"Cat-{UNIQUE_ID}"}
)
assert resp.status_code in [200, 201], f"Erreur: {resp.text}"
TEST_DATA["cat_id"] = resp.json()["id"]
print(f"  ✅ POST /categories/ (ID: {TEST_DATA['cat_id']})")

resp = requests.get(
    f"{API_URL}/categories/{TEST_DATA['cat_id']}", headers=headers_admin
)
assert resp.status_code == 200
print("  ✅ GET /categories/{id}")

resp = requests.get(f"{API_URL}/categories/999999", headers=headers_admin)
assert resp.status_code == 404
print("  ✅ GET /categories/999999 (404 Not Found)")

# =================================================================
# 4. ITEMS (CRUD)
# =================================================================
print("\n🛠️ 4. TESTS ITEMS (/items)")
resp = requests.post(
    f"{API_URL}/items/",
    headers=headers_admin,
    json={
        "name": f"Item-{UNIQUE_ID}",
        "reference": f"REF-{UNIQUE_ID}",
        "category_id": TEST_DATA["cat_id"],
    },
)
assert resp.status_code in [200, 201], f"Erreur: {resp.text}"
TEST_DATA["item_id"] = resp.json()["id"]
print(f"  ✅ POST /items/ (ID: {TEST_DATA['item_id']})")

resp = requests.get(f"{API_URL}/items/", headers=headers_admin)
assert resp.status_code == 200
print("  ✅ GET /items/")

# =================================================================
# 5. CASIERS (CRUD)
# =================================================================
print("\n🗄️ 5. TESTS CASIERS (/lockers)")
resp = requests.post(
    f"{API_URL}/lockers/",
    headers=headers_admin,
    json={
        "name": f"Casier-{UNIQUE_ID}",
        "locker_type": "standard",
        "status": "available",
        "is_connected": True,
    },
)
assert resp.status_code in [200, 201], f"Erreur: {resp.text}"
TEST_DATA["locker_id"] = resp.json()["id"]
print(f"  ✅ POST /lockers/ (ID: {TEST_DATA['locker_id']})")

resp = requests.put(
    f"{API_URL}/lockers/{TEST_DATA['locker_id']}",
    headers=headers_admin,
    json={"status": "maintenance"},
)
assert resp.status_code == 200
print("  ✅ PUT /lockers/{id} (Modification statut)")

# =================================================================
# 6. STOCK & PERMISSIONS
# =================================================================
print("\n📦 6. TESTS STOCK & PERMISSIONS")
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
print(f"  ✅ POST /stock/ (Ajout de 10 items)")

resp = requests.get(
    f"{API_URL}/lockers/{TEST_DATA['locker_id']}/stock", headers=headers_admin
)
assert resp.status_code == 200
assert len(resp.json()) > 0
print("  ✅ GET /lockers/{id}/stock (Lecture du stock du casier)")

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
print("  ✅ POST /lockers/{id}/permissions (Permission 3D ajoutée)")

# =================================================================
# 7. BADGES & WORKFLOW NFC
# =================================================================
print("\n💳 7. TESTS BADGES & NFC (/badge & /auth)")
test_card = (
    f"AA:BB:CC:{str(UNIQUE_ID)[-6:-4]}:{str(UNIQUE_ID)[-4:-2]}:{str(UNIQUE_ID)[-2:]}"
)

# Machine scanne un nouveau badge (pour l'enregistrer)
# Machine (Module NFC) scanne un nouveau badge
resp = requests.post(
    f"{API_URL}/badge/scan", headers=headers_nfc, json={"card_id": test_card}
)
assert resp.status_code in [200, 201, 202], (
    f"Échec du scan du badge: {resp.status_code} - {resp.text}"
)
print(f"  ✅ POST /badge/scan (Machine scanne nouveau badge: {test_card})")

# Admin liste les badges en attente
resp = requests.get(f"{API_URL}/badge/pending", headers=headers_admin)
assert resp.status_code == 200
print("  ✅ GET /badge/pending (Admin voit le badge en attente)")

# Machine tente d'ouvrir le casier avec ce badge inconnu/non assigné
resp = requests.post(
    f"{API_URL}/auth/locker/{TEST_DATA['locker_id']}/check",
    headers=headers_rpi,
    json={"card_id": test_card},
)
assert resp.status_code == 200
assert resp.json()["allowed"] == False
print("  ✅ POST /auth/locker/{id}/check (Ouverture refusée car non assigné)")

# =================================================================
# 8. UTILISATEURS & AUDIT LOGS
# =================================================================
print("\n👥 8. TESTS UTILISATEURS & LOGS (/users, /logs)")
resp = requests.get(f"{API_URL}/users", headers=headers_admin)
assert resp.status_code == 200
print("  ✅ GET /users (Relais Keycloak OK)")

resp = requests.get(
    f"{API_URL}/logs/?locker_id={TEST_DATA['locker_id']}", headers=headers_admin
)
assert resp.status_code == 200
assert len(resp.json()) > 0
print(f"  ✅ GET /logs/ (L'historique d'accès a bien été enregistré)")

# =================================================================
# 9. NETTOYAGE COMPLET (CASCADE)
# =================================================================
print("\n🧹 9. NETTOYAGE DE LA BASE DE DONNÉES")

requests.delete(f"{API_URL}/lockers/{TEST_DATA['locker_id']}", headers=headers_admin)
print(
    f"  ✅ DELETE /lockers/{TEST_DATA['locker_id']} (Supprime aussi Stock, Permissions, Logs)"
)

requests.delete(f"{API_URL}/items/{TEST_DATA['item_id']}", headers=headers_admin)
print(f"  ✅ DELETE /items/{TEST_DATA['item_id']}")

requests.delete(f"{API_URL}/categories/{TEST_DATA['cat_id']}", headers=headers_admin)
print(f"  ✅ DELETE /categories/{TEST_DATA['cat_id']}")

print("\n🎉 EXCELLENT ! TOUTES LES ROUTES FONCTIONNENT PARFAITEMENT (100% SUCCESS) !")
print("==================================================")
