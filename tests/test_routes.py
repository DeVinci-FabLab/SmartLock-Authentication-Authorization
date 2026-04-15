"""
Comprehensive pytest test suite for SmartLock API routes.
Covers: auth.py, roles.py, keycloak.py role guards, and CRUD routes.
All Keycloak HTTP calls are mocked.
"""
import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))
os.environ["DATABASE_URL"] = "sqlite:///:memory:"

from src.routes.auth import _is_expired  # noqa: E402


# ===========================================================================
# _is_expired — pure unit tests (no DB, no HTTP)
# ===========================================================================


class TestIsExpired:
    def test_none_returns_false(self):
        now = datetime.now(timezone.utc)
        assert _is_expired(None, now) is False

    def test_empty_string_returns_false(self):
        now = datetime.now(timezone.utc)
        assert _is_expired("", now) is False

    def test_future_date_not_expired(self):
        now = datetime.now(timezone.utc)
        future = (now + timedelta(days=1)).isoformat()
        assert _is_expired(future, now) is False

    def test_past_date_is_expired(self):
        now = datetime.now(timezone.utc)
        past = (now - timedelta(seconds=1)).isoformat()
        assert _is_expired(past, now) is True

    def test_exact_now_is_expired(self):
        now = datetime.now(timezone.utc)
        assert _is_expired(now.isoformat(), now) is True

    def test_invalid_format_returns_false(self):
        now = datetime.now(timezone.utc)
        assert _is_expired("not-a-date", now) is False

    def test_naive_datetime_treated_as_utc_future(self):
        now = datetime.now(timezone.utc)
        naive_future = (now + timedelta(days=1)).replace(tzinfo=None).isoformat()
        assert _is_expired(naive_future, now) is False

    def test_naive_datetime_treated_as_utc_past(self):
        now = datetime.now(timezone.utc)
        naive_past = (now - timedelta(seconds=1)).replace(tzinfo=None).isoformat()
        assert _is_expired(naive_past, now) is True


# ===========================================================================
# Keycloak dependency guards (require_* functions)
# Tested via routes that use them, with payloads injected via conftest fixtures
# ===========================================================================


class TestRequireAdmin:
    """GET /users requires require_admin (admin only)."""

    def test_admin_role_allowed(self, admin_client):
        with patch("src.routes.users.list_users", new_callable=AsyncMock) as m:
            m.return_value = []
            resp = admin_client.get("/users")
        assert resp.status_code == 200

    def test_codir_denied(self, codir_client):
        resp = codir_client.get("/users")
        assert resp.status_code == 403

    def test_materialiste_denied(self, materialiste_client):
        resp = materialiste_client.get("/users")
        assert resp.status_code == 403

    def test_membre_denied(self, membre_client):
        resp = membre_client.get("/users")
        assert resp.status_code == 403

    def test_unauthenticated_denied(self, client):
        resp = client.get("/users")
        assert resp.status_code in (401, 403)


class TestRequireCodirOrAdmin:
    """GET /logs/ requires require_codir_or_admin."""

    def test_admin_allowed(self, admin_client):
        resp = admin_client.get("/logs/")
        assert resp.status_code == 200

    def test_codir_allowed(self, codir_client):
        resp = codir_client.get("/logs/")
        assert resp.status_code == 200

    def test_materialiste_denied(self, materialiste_client):
        resp = materialiste_client.get("/logs/")
        assert resp.status_code == 403

    def test_membre_denied(self, membre_client):
        resp = membre_client.get("/logs/")
        assert resp.status_code == 403


class TestRequireMaterialisteOrAbove:
    """POST /users/{id}/roles/{role} requires require_materialiste_or_above."""

    def test_materialiste_allowed(self, materialiste_client):
        with patch("src.routes.roles.add_role_to_user", new_callable=AsyncMock) as m:
            m.return_value = None
            resp = materialiste_client.post("/users/any-user/roles/membre")
        assert resp.status_code == 204

    def test_codir_allowed(self, codir_client):
        with patch("src.routes.roles.add_role_to_user", new_callable=AsyncMock) as m:
            m.return_value = None
            resp = codir_client.post("/users/any-user/roles/membre")
        assert resp.status_code == 204

    def test_admin_allowed(self, admin_client):
        with patch("src.routes.roles.add_role_to_user", new_callable=AsyncMock) as m:
            m.return_value = None
            resp = admin_client.post("/users/any-user/roles/membre")
        assert resp.status_code == 204

    def test_membre_denied(self, membre_client):
        resp = membre_client.post("/users/any-user/roles/membre")
        assert resp.status_code == 403


class TestRequireCodir:
    """POST /auth/elevate requires require_codir."""

    def test_codir_allowed(self, codir_client):
        with patch("src.routes.auth.add_role_to_user", new_callable=AsyncMock) as m:
            m.return_value = None
            resp = codir_client.post("/auth/elevate")
        assert resp.status_code == 200

    def test_admin_only_denied(self, admin_client):
        # admin_client has "admin" but NOT "codir" — require_codir must block it
        # NOTE: admin_client fixture does NOT override require_codir
        resp = admin_client.post("/auth/elevate")
        assert resp.status_code == 403

    def test_membre_denied(self, membre_client):
        resp = membre_client.post("/auth/elevate")
        assert resp.status_code == 403


class TestRequireNfcScanner:
    """POST /badge/scan requires require_nfc_scanner."""

    def test_nfc_client_allowed(self, nfc_client):
        resp = nfc_client.post("/badge/scan", json={"card_id": "AA:BB:CC"})
        assert resp.status_code == 201

    def test_admin_denied(self, admin_client):
        resp = admin_client.post("/badge/scan", json={"card_id": "AA:BB:CC"})
        assert resp.status_code == 403


class TestRequireLockerClient:
    """POST /auth/locker/{id}/check requires require_locker_client."""

    def test_rpi_client_allowed(self, rpi_client):
        with patch("src.routes.auth.find_user_by_card_id", new_callable=AsyncMock) as m:
            m.return_value = None  # card not found → denied, but route returns 200
            resp = rpi_client.post(
                "/auth/locker/1/check", json={"card_id": "UNKNOWN"}
            )
        assert resp.status_code == 200
        assert resp.json()["allowed"] is False

    def test_admin_denied(self, admin_client):
        resp = admin_client.post(
            "/auth/locker/1/check", json={"card_id": "CARD"}
        )
        assert resp.status_code == 403


# ===========================================================================
# POST /auth/locker/{locker_id}/check
# ===========================================================================

from src.models.locker_permission import Locker_Permission  # noqa: E402


def _make_locker_permission(
    db,
    locker_id,
    subject_type="role",
    role_name=None,
    user_id=None,
    can_open=False,
    can_view=True,
    valid_until=None,
):
    """Insert a Locker_Permission row into the test DB and return it."""
    perm = Locker_Permission(
        locker_id=locker_id,
        subject_type=subject_type,
        role_name=role_name,
        user_id=user_id,
        can_open=can_open,
        can_view=can_view,
        valid_until=valid_until,
    )
    db.add(perm)
    db.commit()
    db.refresh(perm)
    return perm


class TestLockerAccessCheck:
    LOCKER_ID = 99

    def test_card_not_registered_returns_denied(self, rpi_client):
        with patch("src.routes.auth.find_user_by_card_id", new_callable=AsyncMock) as m:
            m.return_value = None
            resp = rpi_client.post(
                f"/auth/locker/{self.LOCKER_ID}/check",
                json={"card_id": "UNKNOWN_CARD"},
            )
        assert resp.status_code == 200
        body = resp.json()
        assert body["allowed"] is False
        assert body["reason"] == "card_not_registered"

    def test_card_not_registered_creates_access_log(self, rpi_client, db):
        from src.models.access_log import AccessLog

        with patch("src.routes.auth.find_user_by_card_id", new_callable=AsyncMock) as m:
            m.return_value = None
            rpi_client.post(
                f"/auth/locker/{self.LOCKER_ID}/check",
                json={"card_id": "GHOST_CARD"},
            )
        logs = db.query(AccessLog).filter(AccessLog.card_id == "GHOST_CARD").all()
        assert len(logs) == 1
        assert logs[0].result == "denied"
        assert logs[0].reason == "card_not_registered"

    def test_keycloak_error_on_find_user_returns_denied(self, rpi_client):
        with patch("src.routes.auth.find_user_by_card_id", new_callable=AsyncMock) as m:
            m.side_effect = RuntimeError("network failure")
            resp = rpi_client.post(
                f"/auth/locker/{self.LOCKER_ID}/check",
                json={"card_id": "ANY_CARD"},
            )
        assert resp.status_code == 200
        assert resp.json()["allowed"] is False
        assert resp.json()["reason"] == "keycloak_error"

    def test_keycloak_error_on_get_roles_returns_denied(self, rpi_client):
        with patch(
            "src.routes.auth.find_user_by_card_id", new_callable=AsyncMock
        ) as fu, patch(
            "src.routes.auth.get_user_effective_roles", new_callable=AsyncMock
        ) as gr:
            fu.return_value = {"id": "user-1", "firstName": "Bob", "lastName": ""}
            gr.side_effect = RuntimeError("roles unavailable")
            resp = rpi_client.post(
                f"/auth/locker/{self.LOCKER_ID}/check",
                json={"card_id": "BOB_CARD"},
            )
        assert resp.status_code == 200
        assert resp.json()["allowed"] is False
        assert resp.json()["reason"] == "keycloak_error"

    def test_no_permissions_row_returns_denied(self, rpi_client):
        with patch(
            "src.routes.auth.find_user_by_card_id", new_callable=AsyncMock
        ) as fu, patch(
            "src.routes.auth.get_user_effective_roles", new_callable=AsyncMock
        ) as gr:
            fu.return_value = {"id": "user-1", "firstName": "Alice", "lastName": "D"}
            gr.return_value = ["admin", "membre"]
            resp = rpi_client.post(
                f"/auth/locker/{self.LOCKER_ID}/check",
                json={"card_id": "ALICE_CARD"},
            )
        assert resp.status_code == 200
        assert resp.json()["allowed"] is False
        assert resp.json()["reason"] == "no_permission"

    def test_role_permission_can_open_false_denied(self, rpi_client, db):
        _make_locker_permission(db, self.LOCKER_ID, role_name="admin", can_open=False)
        with patch(
            "src.routes.auth.find_user_by_card_id", new_callable=AsyncMock
        ) as fu, patch(
            "src.routes.auth.get_user_effective_roles", new_callable=AsyncMock
        ) as gr:
            fu.return_value = {"id": "user-1", "firstName": "Alice", "lastName": "D"}
            gr.return_value = ["admin"]
            resp = rpi_client.post(
                f"/auth/locker/{self.LOCKER_ID}/check",
                json={"card_id": "ALICE_CARD"},
            )
        assert resp.status_code == 200
        assert resp.json()["allowed"] is False

    def test_role_permission_can_open_true_allowed(self, rpi_client, db):
        _make_locker_permission(db, self.LOCKER_ID, role_name="admin", can_open=True)
        with patch(
            "src.routes.auth.find_user_by_card_id", new_callable=AsyncMock
        ) as fu, patch(
            "src.routes.auth.get_user_effective_roles", new_callable=AsyncMock
        ) as gr:
            fu.return_value = {"id": "user-1", "firstName": "Alice", "lastName": "D"}
            gr.return_value = ["admin"]
            resp = rpi_client.post(
                f"/auth/locker/{self.LOCKER_ID}/check",
                json={"card_id": "ALICE_CARD"},
            )
        assert resp.status_code == 200
        assert resp.json()["allowed"] is True
        assert resp.json()["display_name"] == "Alice D"

    def test_multiple_role_permissions_are_ored(self, rpi_client, db):
        # "membre" has can_open=False, "admin" has can_open=True → OR → allowed
        _make_locker_permission(db, self.LOCKER_ID, role_name="membre", can_open=False)
        _make_locker_permission(db, self.LOCKER_ID, role_name="admin", can_open=True)
        with patch(
            "src.routes.auth.find_user_by_card_id", new_callable=AsyncMock
        ) as fu, patch(
            "src.routes.auth.get_user_effective_roles", new_callable=AsyncMock
        ) as gr:
            fu.return_value = {"id": "user-1", "username": "alice"}
            gr.return_value = ["admin", "membre"]
            resp = rpi_client.post(
                f"/auth/locker/{self.LOCKER_ID}/check",
                json={"card_id": "ALICE_CARD"},
            )
        assert resp.json()["allowed"] is True

    def test_expired_role_permission_is_skipped(self, rpi_client, db):
        past = (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat()
        _make_locker_permission(
            db, self.LOCKER_ID, role_name="admin", can_open=True, valid_until=past
        )
        with patch(
            "src.routes.auth.find_user_by_card_id", new_callable=AsyncMock
        ) as fu, patch(
            "src.routes.auth.get_user_effective_roles", new_callable=AsyncMock
        ) as gr:
            fu.return_value = {"id": "user-1", "username": "alice"}
            gr.return_value = ["admin"]
            resp = rpi_client.post(
                f"/auth/locker/{self.LOCKER_ID}/check",
                json={"card_id": "ALICE_CARD"},
            )
        assert resp.json()["allowed"] is False
        assert resp.json()["reason"] == "no_permission"

    def test_user_permission_overrides_role_permission(self, rpi_client, db):
        # Role says can_open=False, user-specific says can_open=True
        _make_locker_permission(db, self.LOCKER_ID, role_name="admin", can_open=False)
        _make_locker_permission(
            db, self.LOCKER_ID, subject_type="user", user_id="user-1", can_open=True
        )
        with patch(
            "src.routes.auth.find_user_by_card_id", new_callable=AsyncMock
        ) as fu, patch(
            "src.routes.auth.get_user_effective_roles", new_callable=AsyncMock
        ) as gr:
            fu.return_value = {"id": "user-1", "username": "alice"}
            gr.return_value = ["admin"]
            resp = rpi_client.post(
                f"/auth/locker/{self.LOCKER_ID}/check",
                json={"card_id": "ALICE_CARD"},
            )
        assert resp.json()["allowed"] is True

    def test_user_permission_can_deny_despite_open_role(self, rpi_client, db):
        # Role says can_open=True, user-specific says can_open=False → denied
        _make_locker_permission(db, self.LOCKER_ID, role_name="admin", can_open=True)
        _make_locker_permission(
            db, self.LOCKER_ID, subject_type="user", user_id="user-1", can_open=False
        )
        with patch(
            "src.routes.auth.find_user_by_card_id", new_callable=AsyncMock
        ) as fu, patch(
            "src.routes.auth.get_user_effective_roles", new_callable=AsyncMock
        ) as gr:
            fu.return_value = {"id": "user-1", "username": "alice"}
            gr.return_value = ["admin"]
            resp = rpi_client.post(
                f"/auth/locker/{self.LOCKER_ID}/check",
                json={"card_id": "ALICE_CARD"},
            )
        assert resp.json()["allowed"] is False

    def test_expired_user_perm_falls_back_to_role(self, rpi_client, db):
        # User perm is expired — role perm is active with can_open=True → allowed
        past = (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat()
        _make_locker_permission(db, self.LOCKER_ID, role_name="admin", can_open=True)
        _make_locker_permission(
            db,
            self.LOCKER_ID,
            subject_type="user",
            user_id="user-1",
            can_open=False,
            valid_until=past,
        )
        with patch(
            "src.routes.auth.find_user_by_card_id", new_callable=AsyncMock
        ) as fu, patch(
            "src.routes.auth.get_user_effective_roles", new_callable=AsyncMock
        ) as gr:
            fu.return_value = {"id": "user-1", "username": "alice"}
            gr.return_value = ["admin"]
            resp = rpi_client.post(
                f"/auth/locker/{self.LOCKER_ID}/check",
                json={"card_id": "ALICE_CARD"},
            )
        assert resp.json()["allowed"] is True

    def test_display_name_from_first_and_last(self, rpi_client, db):
        _make_locker_permission(db, self.LOCKER_ID, role_name="admin", can_open=True)
        with patch(
            "src.routes.auth.find_user_by_card_id", new_callable=AsyncMock
        ) as fu, patch(
            "src.routes.auth.get_user_effective_roles", new_callable=AsyncMock
        ) as gr:
            fu.return_value = {"id": "user-1", "firstName": "Jean", "lastName": "Dupont"}
            gr.return_value = ["admin"]
            resp = rpi_client.post(
                f"/auth/locker/{self.LOCKER_ID}/check",
                json={"card_id": "JEAN_CARD"},
            )
        assert resp.json()["display_name"] == "Jean Dupont"

    def test_display_name_falls_back_to_username(self, rpi_client, db):
        _make_locker_permission(db, self.LOCKER_ID, role_name="admin", can_open=True)
        with patch(
            "src.routes.auth.find_user_by_card_id", new_callable=AsyncMock
        ) as fu, patch(
            "src.routes.auth.get_user_effective_roles", new_callable=AsyncMock
        ) as gr:
            fu.return_value = {
                "id": "user-1",
                "firstName": "",
                "lastName": "",
                "username": "jean.d",
            }
            gr.return_value = ["admin"]
            resp = rpi_client.post(
                f"/auth/locker/{self.LOCKER_ID}/check",
                json={"card_id": "JEAN_CARD"},
            )
        assert resp.json()["display_name"] == "jean.d"

    def test_display_name_falls_back_to_unknown(self, rpi_client, db):
        _make_locker_permission(db, self.LOCKER_ID, role_name="admin", can_open=True)
        with patch(
            "src.routes.auth.find_user_by_card_id", new_callable=AsyncMock
        ) as fu, patch(
            "src.routes.auth.get_user_effective_roles", new_callable=AsyncMock
        ) as gr:
            fu.return_value = {"id": "user-1"}
            gr.return_value = ["admin"]
            resp = rpi_client.post(
                f"/auth/locker/{self.LOCKER_ID}/check",
                json={"card_id": "ANON_CARD"},
            )
        assert resp.json()["display_name"] == "Utilisateur inconnu"

    def test_access_log_created_on_allowed(self, rpi_client, db):
        from src.models.access_log import AccessLog

        _make_locker_permission(db, self.LOCKER_ID, role_name="admin", can_open=True)
        with patch(
            "src.routes.auth.find_user_by_card_id", new_callable=AsyncMock
        ) as fu, patch(
            "src.routes.auth.get_user_effective_roles", new_callable=AsyncMock
        ) as gr:
            fu.return_value = {"id": "user-log", "firstName": "Test", "lastName": "User"}
            gr.return_value = ["admin"]
            rpi_client.post(
                f"/auth/locker/{self.LOCKER_ID}/check",
                json={"card_id": "LOG_CARD"},
            )
        logs = db.query(AccessLog).filter(AccessLog.card_id == "LOG_CARD").all()
        assert len(logs) == 1
        assert logs[0].result == "allowed"
        assert logs[0].user_id == "user-log"

    def test_access_log_created_on_denied(self, rpi_client, db):
        from src.models.access_log import AccessLog

        with patch(
            "src.routes.auth.find_user_by_card_id", new_callable=AsyncMock
        ) as fu, patch(
            "src.routes.auth.get_user_effective_roles", new_callable=AsyncMock
        ) as gr:
            fu.return_value = {"id": "user-2", "username": "bob"}
            gr.return_value = ["membre"]
            rpi_client.post(
                f"/auth/locker/{self.LOCKER_ID}/check",
                json={"card_id": "BOB_CARD_DENIED"},
            )
        logs = db.query(AccessLog).filter(AccessLog.card_id == "BOB_CARD_DENIED").all()
        assert len(logs) == 1
        assert logs[0].result == "denied"


# ===========================================================================
# POST /auth/elevate  (require_codir)
# ===========================================================================


class TestElevateToAdmin:
    def test_codir_elevates_successfully(self, codir_client):
        with patch("src.routes.auth.add_role_to_user", new_callable=AsyncMock) as m:
            m.return_value = None
            resp = codir_client.post("/auth/elevate")
        assert resp.status_code == 200
        assert "admin" in resp.json()["message"].lower() or "accordé" in resp.json()["message"]
        m.assert_called_once_with("codir-456", "admin")

    def test_codir_already_has_admin_returns_message(self, db):
        """Codir who already has admin role gets an informational 200, no Keycloak call."""
        from src.core.keycloak import require_codir, validate_jwt
        from src.database.session import get_db
        from src.main import app
        from fastapi.testclient import TestClient

        payload = {
            "sub": "codir-with-admin",
            "realm_access": {"roles": ["codir", "admin"]},
        }

        def override_db():
            yield db

        app.dependency_overrides[get_db] = override_db
        app.dependency_overrides[validate_jwt] = lambda: payload
        app.dependency_overrides[require_codir] = lambda: payload

        try:
            with TestClient(app) as c:
                with patch("src.routes.auth.add_role_to_user", new_callable=AsyncMock) as m:
                    resp = c.post("/auth/elevate")
        finally:
            app.dependency_overrides.clear()

        assert resp.status_code == 200
        assert "déjà" in resp.json()["message"]
        m.assert_not_called()

    def test_membre_cannot_elevate(self, membre_client):
        resp = membre_client.post("/auth/elevate")
        assert resp.status_code == 403

    def test_admin_only_cannot_elevate(self, admin_client):
        # admin_client has "admin" but NOT "codir" — require_codir should reject it
        resp = admin_client.post("/auth/elevate")
        assert resp.status_code == 403


# ===========================================================================
# POST /auth/revoke-admin  (require_admin)
# ===========================================================================


class TestRevokeAdmin:
    def test_admin_revokes_successfully(self, admin_client):
        with patch("src.routes.auth.remove_role_from_user", new_callable=AsyncMock) as m:
            m.return_value = None
            resp = admin_client.post("/auth/revoke-admin")
        assert resp.status_code == 200
        body = resp.json()
        assert "révoqué" in body["message"] or "revoque" in body["message"].lower()
        m.assert_called_once_with("admin-123", "admin")

    def test_codir_cannot_revoke(self, codir_client):
        resp = codir_client.post("/auth/revoke-admin")
        assert resp.status_code == 403

    def test_membre_cannot_revoke(self, membre_client):
        resp = membre_client.post("/auth/revoke-admin")
        assert resp.status_code == 403


# ===========================================================================
# POST/DELETE /users/{user_id}/roles/{role_name}  — permission matrix
# ===========================================================================


@pytest.mark.parametrize(
    "role,expected_status",
    [
        ("membre", 204),
        ("3d", 204),
        ("electronique", 403),
        ("textile", 403),
        ("materialiste", 403),
        ("admin", 403),
        ("codir", 403),
    ],
)
def test_materialiste_role_assignment_matrix(materialiste_client, role, expected_status):
    with patch("src.routes.roles.add_role_to_user", new_callable=AsyncMock) as m:
        m.return_value = None
        resp = materialiste_client.post(f"/users/target-user/roles/{role}")
    assert resp.status_code == expected_status, (
        f"Materialiste assigning '{role}': expected {expected_status}, got {resp.status_code}"
    )


@pytest.mark.parametrize(
    "role,expected_status",
    [
        ("membre", 204),
        ("3d", 204),
        ("electronique", 204),
        ("textile", 204),
        ("materialiste", 204),
        ("admin", 204),
        ("codir", 403),
    ],
)
def test_codir_role_assignment_matrix(codir_client, role, expected_status):
    with patch("src.routes.roles.add_role_to_user", new_callable=AsyncMock) as m:
        m.return_value = None
        resp = codir_client.post(f"/users/target-user/roles/{role}")
    assert resp.status_code == expected_status, (
        f"Codir assigning '{role}': expected {expected_status}, got {resp.status_code}"
    )


@pytest.mark.parametrize(
    "role,expected_status",
    [
        ("membre", 204),
        ("3d", 204),
        ("electronique", 204),
        ("textile", 204),
        ("materialiste", 204),
        ("admin", 204),
        ("codir", 204),
    ],
)
def test_admin_role_assignment_matrix(admin_client, role, expected_status):
    with patch("src.routes.roles.add_role_to_user", new_callable=AsyncMock) as m:
        m.return_value = None
        resp = admin_client.post(f"/users/target-user/roles/{role}")
    assert resp.status_code == expected_status, (
        f"Admin assigning '{role}': expected {expected_status}, got {resp.status_code}"
    )


class TestRoleManagement:
    def test_unknown_role_returns_400(self, admin_client):
        resp = admin_client.post("/users/any-user/roles/role-inconnu")
        assert resp.status_code == 400

    def test_unknown_role_for_materialiste_returns_400(self, materialiste_client):
        resp = materialiste_client.post("/users/any-user/roles/superpower")
        assert resp.status_code == 400

    def test_delete_role_materialiste_revokes_membre(self, materialiste_client):
        with patch("src.routes.roles.remove_role_from_user", new_callable=AsyncMock) as m:
            m.return_value = None
            resp = materialiste_client.delete("/users/target-user/roles/membre")
        assert resp.status_code == 204
        m.assert_called_once_with("target-user", "membre")

    def test_delete_role_materialiste_cannot_revoke_electronique(self, materialiste_client):
        resp = materialiste_client.delete("/users/target-user/roles/electronique")
        assert resp.status_code == 403

    def test_delete_role_codir_can_revoke_electronique(self, codir_client):
        with patch("src.routes.roles.remove_role_from_user", new_callable=AsyncMock) as m:
            m.return_value = None
            resp = codir_client.delete("/users/target-user/roles/electronique")
        assert resp.status_code == 204

    def test_delete_role_codir_cannot_revoke_codir(self, codir_client):
        resp = codir_client.delete("/users/target-user/roles/codir")
        assert resp.status_code == 403

    def test_delete_role_admin_can_revoke_codir(self, admin_client):
        with patch("src.routes.roles.remove_role_from_user", new_callable=AsyncMock) as m:
            m.return_value = None
            resp = admin_client.delete("/users/target-user/roles/codir")
        assert resp.status_code == 204

    def test_membre_cannot_manage_any_role(self, membre_client):
        resp = membre_client.post("/users/any-user/roles/membre")
        assert resp.status_code == 403


# ===========================================================================
# CRUD routes (categories, items, lockers, stock, badge, logs)
# ===========================================================================


class TestCRUDRoutes:
    def test_create_category_as_admin(self, admin_client):
        resp = admin_client.post("/categories/", json={"name": "Outillage"})
        assert resp.status_code == 201
        data = resp.json()
        assert data["name"] == "Outillage"
        assert "id" in data

    def test_create_category_as_membre_forbidden(self, membre_client):
        resp = membre_client.post("/categories/", json={"name": "X"})
        assert resp.status_code == 403

    def test_create_item_as_admin(self, admin_client):
        cat_resp = admin_client.post("/categories/", json={"name": "Perçage"})
        assert cat_resp.status_code == 201
        cat_id = cat_resp.json()["id"]

        resp = admin_client.post(
            "/items/",
            json={"name": "Perceuse", "reference": "P-01", "category_id": cat_id},
        )
        assert resp.status_code == 201
        assert resp.json()["name"] == "Perceuse"

    def test_create_locker_as_admin(self, admin_client):
        resp = admin_client.post("/lockers/", json={"locker_type": "standard"})
        assert resp.status_code == 201
        assert "id" in resp.json()

    def test_add_stock_as_admin(self, admin_client):
        cat = admin_client.post("/categories/", json={"name": "Cat"}).json()
        item = admin_client.post(
            "/items/",
            json={"name": "Item", "reference": "REF-99", "category_id": cat["id"]},
        ).json()
        locker = admin_client.post("/lockers/", json={"locker_type": "standard"}).json()

        resp = admin_client.post(
            "/stock/",
            json={"locker_id": locker["id"], "item_id": item["id"], "quantity": 5},
        )
        assert resp.status_code == 201

    def test_scan_badge_as_nfc(self, nfc_client):
        resp = nfc_client.post("/badge/scan", json={"card_id": "AA:BB:CC:11:22"})
        assert resp.status_code == 201

    def test_read_logs_as_admin(self, admin_client):
        resp = admin_client.get("/logs/")
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

    def test_read_logs_filtered_by_locker(self, admin_client):
        resp = admin_client.get("/logs/?locker_id=1")
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)


# ===========================================================================
# System endpoints
# ===========================================================================


class TestSystemEndpoints:
    def test_health_check(self, client):
        resp = client.get("/health")
        assert resp.status_code == 200
        body = resp.json()
        assert body["status"] == "healthy"
        assert body["service"] == "Smartlock API"
        assert body["version"] == "0.1.0"

    def test_root(self, client):
        resp = client.get("/")
        assert resp.status_code == 200
        body = resp.json()
        assert "message" in body
        assert body["docs"] == "/docs"
        assert body["health"] == "/health"
        assert body["version"] == "0.1.0"

    def test_validation_error_returns_422(self, admin_client):
        # Missing required 'name' field
        resp = admin_client.post("/categories/", json={})
        assert resp.status_code == 422

    def test_unknown_route_returns_404(self, client):
        resp = client.get("/this-does-not-exist")
        assert resp.status_code == 404
