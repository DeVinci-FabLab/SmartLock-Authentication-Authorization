import os
import sys
from pathlib import Path
from unittest.mock import AsyncMock, patch

# 1. Force Python à inclure la racine du projet
sys.path.insert(0, str(Path(__file__).parent.parent))

# 2. SÉCURITÉ : Forcer SQLite en mémoire AVANT d'importer l'application
os.environ["DATABASE_URL"] = "sqlite:///:memory:"

from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import create_engine  # noqa: E402
from sqlalchemy.orm import sessionmaker  # noqa: E402
from sqlalchemy.pool import StaticPool  # noqa: E402

from src.core.keycloak import (  # noqa: E402
    require_admin,
    require_locker_client,
    require_nfc_scanner,
    validate_jwt,
)
from src.database.base import Base  # noqa: E402
from src.database.session import get_db  # noqa: E402
from src.main import app, limiter  # noqa: E402

# --- CONFIGURATION DE L'ENVIRONNEMENT DE TEST ---

# Désactiver le limiteur de requêtes pour éviter les erreurs 429
limiter.enabled = False

# Configurer la BDD en mémoire
engine = create_engine(
    "sqlite:///:memory:",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(
    autocommit=False, autoflush=False, bind=engine
)
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
    fake_payload = {
        "sub": "admin-123",
        "realm_access": {"roles": ["admin", "membre"]},
    }
    app.dependency_overrides[validate_jwt] = lambda: fake_payload
    app.dependency_overrides[require_admin] = lambda: fake_payload


def set_role_nfc_scanner():
    """Simule la borne d'accueil NFC."""
    app.dependency_overrides.clear()
    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[require_nfc_scanner] = (
        lambda: {"azp": "nfc-scanner"}
    )


def set_role_raspberry_pi():
    """Simule le terminal d'un casier."""
    app.dependency_overrides.clear()
    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[require_locker_client] = (
        lambda: {"azp": "smartlock-lockers"}
    )


# --- SCRIPT PRINCIPAL ---


def run_tests():
    print(
        "Demarrage des tests des ROUTES de l'API (Mode Script)...\n"
    )

    # ---------------------------------------------------------
    print("ETAPE 1 : Test du CRUD (Par un Administrateur)")
    set_role_admin()

    print("  Creation d'une categorie...")
    resp = client.post("/categories/", json={"name": "Outillage"})
    cat_id = resp.json().get("id")
    print(
        f"     Resultat : {resp.status_code}"
        f" - Categorie creee (ID: {cat_id})"
    )

    print("  Creation d'un outil...")
    resp = client.post(
        "/items/",
        json={
            "name": "Perceuse",
            "reference": "P-01",
            "category_id": cat_id,
        },
    )
    item_id = resp.json().get("id")
    print(
        f"     Resultat : {resp.status_code}"
        f" - Outil cree (ID: {item_id})"
    )

    print("  Creation d'un casier...")
    resp = client.post(
        "/lockers/", json={"locker_type": "standard"}
    )
    locker_id = resp.json().get("id")
    print(
        f"     Resultat : {resp.status_code}"
        f" - Casier cree (ID: {locker_id})"
    )

    print("  Ajout de stock dans le casier...")
    resp = client.post(
        "/stock/",
        json={
            "locker_id": locker_id,
            "item_id": item_id,
            "quantity": 5,
        },
    )
    print(
        f"     Resultat : {resp.status_code}"
        f" - 5 Perceuses ajoutees au casier {locker_id}"
    )

    # ---------------------------------------------------------
    print("\nETAPE 2 : Test de la Borne NFC (Machine)")
    set_role_nfc_scanner()

    print("  Scan d'un nouveau badge inconnu...")
    resp = client.post(
        "/badge/scan", json={"card_id": "AA:BB:CC:11:22"}
    )
    print(
        f"     Resultat : {resp.status_code}"
        f" - Badge stocke en attente ({resp.json().get('status')})"
    )

    # ---------------------------------------------------------
    print(
        "\nETAPE 3 : Test de l'Armoire Connectee (Raspberry Pi)"
    )
    set_role_raspberry_pi()

    print(
        "  L'armoire demande si un badge a le droit de s'ouvrir..."
    )

    # Simuler la reponse de Keycloak
    with patch(
        "src.routes.auth.find_user_by_card_id",
        new_callable=AsyncMock,
    ) as mock_find_user, patch(
        "src.routes.auth.get_user_effective_roles",
        new_callable=AsyncMock,
    ) as mock_get_roles:
        mock_find_user.return_value = {
            "id": "user-123",
            "firstName": "Alice",
            "lastName": "Dupont",
        }
        mock_get_roles.return_value = ["admin", "membre"]

        resp = client.post(
            f"/auth/locker/{locker_id}/check",
            json={"card_id": "KNOWN_BADGE"},
        )

        data = resp.json()
        if data.get("allowed"):
            name = data.get("display_name")
            print(
                f"     Resultat : {resp.status_code}"
                f" - ACCES AUTORISE pour {name} !"
            )
        else:
            reason = data.get("reason")
            print(
                f"     Resultat : {resp.status_code}"
                f" - ACCES REFUSE (Raison: {reason})"
            )

    # ---------------------------------------------------------
    print(
        "\nETAPE 4 : Verification de l'Audit"
        " (Par un Administrateur)"
    )
    set_role_admin()

    print("  Lecture de l'historique d'acces...")
    resp = client.get("/logs/")
    logs = resp.json()
    print(
        f"     Resultat : {resp.status_code}"
        f" - {len(logs)} evenement(s) enregistre(s)"
    )
    if logs:
        last = logs[-1]
        print(
            f"     Dernier log : {last['username']}"
            f" a badge sur le casier {last['locker_id']}"
            f" -> Resultat : {last['result'].upper()}"
        )

    print("\nFin des tests API !")


if __name__ == "__main__":
    run_tests()
