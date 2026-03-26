import os
import pytest
import requests
from fastapi.testclient import TestClient
from dotenv import load_dotenv

# On importe votre application FastAPI
from src.main import app

load_dotenv()

KEYCLOAK_URL = os.getenv("KEYCLOAK_URL", "https://auth.devinci-fablab.fr")
REALM = os.getenv("KEYCLOAK_REALM", "master")
TOKEN_URL = f"{KEYCLOAK_URL}/realms/{REALM}/protocol/openid-connect/token"


@pytest.fixture(scope="session")
def client():
    """Fournit le client de test FastAPI."""
    return TestClient(app)


@pytest.fixture(scope="session")
def admin_headers():
    """Récupère le token Admin une seule fois pour tous les tests."""
    resp = requests.post(
        TOKEN_URL,
        data={
            "grant_type": "password",
            "client_id": "smartlock-dashboard",
            "username": os.getenv("ADMIN_USERNAME", "florian_c"),
            "password": os.getenv("ADMIN_PASSWORD", ""),
        },
    )
    token = resp.json().get("access_token")
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture(scope="session")
def rpi_headers():
    """Récupère le token du Raspberry Pi."""
    resp = requests.post(
        TOKEN_URL,
        data={
            "grant_type": "client_credentials",
            "client_id": "smartlock-lockers",
            "client_secret": os.getenv("LOCKER_CLIENT_SECRET", ""),
        },
    )
    token = resp.json().get("access_token")
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture(scope="session")
def nfc_headers():
    """Récupère le token du lecteur NFC."""
    resp = requests.post(
        TOKEN_URL,
        data={
            "grant_type": "client_credentials",
            "client_id": "nfc-scanner",
            "client_secret": os.getenv("NFC_CLIENT_SECRET", ""),
        },
    )
    token = resp.json().get("access_token")
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def test_category(client, admin_headers):
    """Fixture qui crée une catégorie avant le test, et la supprime après (Nettoyage automatique)."""
    resp = client.post(
        "/categories/", headers=admin_headers, json={"name": "Catégorie Pytest"}
    )
    cat_id = resp.json()["id"]

    yield cat_id  # Le test s'exécute ici avec cet ID

    # Nettoyage après le test
    client.delete(f"/categories/{cat_id}", headers=admin_headers)


@pytest.fixture
def test_locker(client, admin_headers):
    """Fixture qui crée un casier pour les tests et le nettoie ensuite."""
    resp = client.post(
        "/lockers/",
        headers=admin_headers,
        json={
            "name": "Casier Pytest",
            "locker_type": "standard",
            "status": "available",
            "is_connected": True,
        },
    )
    locker_id = resp.json()["id"]
    yield locker_id
    client.delete(f"/lockers/{locker_id}", headers=admin_headers)
