import os
import sys
from pathlib import Path
from unittest.mock import patch

# 1. Force Python à inclure la racine du projet
sys.path.insert(0, str(Path(__file__).parent.parent))

# 2. SÉCURITÉ : Forcer SQLite en mémoire AVANT d'importer l'application
os.environ["DATABASE_URL"] = "sqlite:///:memory:"

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

# Import de l'application et des dépendances de sécurité
from src.main import app, limiter
from src.database.base import Base
from src.database.session import get_db
from src.core.keycloak import (
    validate_jwt, 
    require_admin, 
    require_locker_client, 
    require_nfc_scanner
)

# --- CONFIGURATION DE L'ENVIRONNEMENT DE TEST ---

# Désactiver le limiteur de requêtes pour éviter les erreurs 429
limiter.enabled = False

# Configurer la BDD en mémoire
engine = create_engine(
    "sqlite:///:memory:",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base.metadata.create_all(bind=engine)

def override_get_db():
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()

# Remplacer la vraie DB par la fausse
app.dependency_overrides[get_db] = override_get_db

# Création du "faux navigateur" pour appeler l'API
client = TestClient(app)


# --- FONCTIONS POUR SIMULER LES DIFFÉRENTS UTILISATEURS ---

def set_role_admin():
    """Donne les pleins pouvoirs à notre client de test."""
    app.dependency_overrides.clear()
    app.dependency_overrides[get_db] = override_get_db
    fake_payload = {"sub": "admin-123", "realm_access": {"roles": ["admin", "membre"]}}
    app.dependency_overrides[validate_jwt] = lambda: fake_payload
    app.dependency_overrides[require_admin] = lambda: fake_payload

def set_role_nfc_scanner():
    """Simule la borne d'accueil NFC."""
    app.dependency_overrides.clear()
    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[require_nfc_scanner] = lambda: {"azp": "nfc-scanner"}

def set_role_raspberry_pi():
    """Simule le terminal d'un casier."""
    app.dependency_overrides.clear()
    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[require_locker_client] = lambda: {"azp": "smartlock-lockers"}


# --- SCRIPT PRINCIPAL ---

def run_tests():
    print("🚀 Démarrage des tests des ROUTES de l'API (Mode Script)...\n")

    # ---------------------------------------------------------
    print("🛠️  ÉTAPE 1 : Test du CRUD (Par un Administrateur)")
    set_role_admin()
    
    print("  🟢 Création d'une catégorie...")
    resp = client.post("/categories/", json={"name": "Outillage"})
    cat_id = resp.json().get("id")
    print(f"     ✅ Résultat : {resp.status_code} - Catégorie créée (ID: {cat_id})")

    print("  🟢 Création d'un outil...")
    resp = client.post("/items/", json={"name": "Perceuse", "reference": "P-01", "category_id": cat_id})
    item_id = resp.json().get("id")
    print(f"     ✅ Résultat : {resp.status_code} - Outil créé (ID: {item_id})")

    print("  🟢 Création d'un casier...")
    resp = client.post("/lockers/", json={"locker_type": "standard"})
    locker_id = resp.json().get("id")
    print(f"     ✅ Résultat : {resp.status_code} - Casier créé (ID: {locker_id})")

    print("  🟢 Ajout de stock dans le casier...")
    resp = client.post("/stock/", json={"locker_id": locker_id, "item_id": item_id, "quantity": 5})
    print(f"     ✅ Résultat : {resp.status_code} - 5 Perceuses ajoutées au casier {locker_id}")

    # ---------------------------------------------------------
    print("\n💳 ÉTAPE 2 : Test de la Borne NFC (Machine)")
    set_role_nfc_scanner()

    print("  🟢 Scan d'un nouveau badge inconnu...")
    resp = client.post("/badge/scan", json={"card_id": "AA:BB:CC:11:22"})
    print(f"     ✅ Résultat : {resp.status_code} - Badge stocké en attente ({resp.json().get('status')})")

    # ---------------------------------------------------------
    print("\n🔒 ÉTAPE 3 : Test de l'Armoire Connectée (Raspberry Pi)")
    set_role_raspberry_pi()

    print("  🟢 L'armoire demande si un badge a le droit de s'ouvrir...")
    
    # Ici on doit "simuler" la réponse de Keycloak car le vrai Keycloak n'a pas notre faux badge
    with patch("src.routes.auth.find_user_by_card_id") as mock_find_user:
        with patch("src.routes.auth.get_user_effective_roles") as mock_get_roles:
            
            # On dit au script : Fais comme si Keycloak connaissait ce badge et lui donnait le rôle 'admin'
            mock_find_user.return_value = {"id": "user-123", "firstName": "Alice", "lastName": "Dupont"}
            mock_get_roles.return_value = ["admin", "membre"]

            resp = client.post(f"/auth/locker/{locker_id}/check", json={"card_id": "KNOWN_BADGE"})
            
            data = resp.json()
            if data.get("allowed"):
                print(f"     ✅ Résultat : {resp.status_code} - ACCÈS AUTORISÉ pour {data.get('display_name')} !")
            else:
                print(f"     ❌ Résultat : {resp.status_code} - ACCÈS REFUSÉ (Raison: {data.get('reason')})")

    # ---------------------------------------------------------
    print("\n🕵️  ÉTAPE 4 : Vérification de l'Audit (Par un Administrateur)")
    set_role_admin()

    print("  🟢 Lecture de l'historique d'accès...")
    resp = client.get("/logs/")
    logs = resp.json()
    print(f"     ✅ Résultat : {resp.status_code} - {len(logs)} événement(s) enregistré(s) en base de données.")
    if logs:
        print(f"     📝 Dernier log : {logs[-1]['username']} a badgé sur le casier {logs[-1]['locker_id']} -> Résultat : {logs[-1]['result'].upper()}")

    print("\n🏁 Fin des tests API !")

if __name__ == "__main__":
    run_tests()