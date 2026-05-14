import pytest
from unittest.mock import AsyncMock, patch
from src.models.role import Role

pytestmark = pytest.mark.anyio


def _seed_system_roles(db):
    db.add(Role(name="admin", label="Admin", tier=5, is_system=True, is_manager=True, is_role_admin=True, capacities=[]))
    db.add(Role(name="codir", label="Codir", tier=3, is_system=True, is_manager=True, is_role_admin=True, capacities=[]))
    db.add(Role(name="membre", label="Membre", tier=0, is_system=True, is_manager=False, is_role_admin=False, capacities=[]))
    db.commit()


class TestGetRoles:
    def test_list_roles_authenticated(self, membre_client, db):
        _seed_system_roles(db)
        resp = membre_client.get("/roles")
        assert resp.status_code == 200
        data = resp.json()
        assert any(r["name"] == "admin" for r in data)

    def test_list_roles_unauthenticated(self, client):
        resp = client.get("/roles")
        assert resp.status_code in (401, 403)


class TestCreateRole:
    def test_create_role_requires_role_admin(self, membre_client, db):
        _seed_system_roles(db)
        resp = membre_client.post("/roles", json={"name": "newrole", "label": "New Role",
                                                   "tier": 1, "is_manager": False, "is_role_admin": False, "capacities": []})
        assert resp.status_code == 403

    def test_create_role_ok(self, admin_client, db):
        _seed_system_roles(db)
        with patch("src.routes.roles_crud.create_realm_role", new_callable=AsyncMock):
            resp = admin_client.post("/roles", json={"name": "agent_fdm", "label": "Agent FDM",
                                                      "tier": 1, "is_manager": False, "is_role_admin": False, "capacities": []})
        assert resp.status_code == 201
        assert resp.json()["name"] == "agent_fdm"

    def test_create_system_role_reserved_tier5(self, admin_client, db):
        """Tier 5 is reserved for system roles — validation rejects it."""
        _seed_system_roles(db)
        resp = admin_client.post("/roles", json={"name": "badrol", "label": "Bad",
                                                  "tier": 5, "is_manager": False, "is_role_admin": False, "capacities": []})
        assert resp.status_code == 422


class TestDeleteRole:
    def test_delete_system_role_forbidden(self, admin_client, db):
        _seed_system_roles(db)
        resp = admin_client.delete("/roles/admin")
        assert resp.status_code == 403
        assert resp.json()["detail"] == "system_role_not_deletable"

    def test_delete_custom_role_ok(self, admin_client, db):
        _seed_system_roles(db)
        db.add(Role(name="custom_r", label="Custom", tier=1, is_system=False,
                    is_manager=False, is_role_admin=False, capacities=[]))
        db.commit()
        with patch("src.routes.roles_crud.get_users_with_role", new_callable=AsyncMock) as m_users, \
             patch("src.routes.roles_crud.delete_realm_role", new_callable=AsyncMock):
            m_users.return_value = []
            resp = admin_client.delete("/roles/custom_r")
        assert resp.status_code == 204

    def test_delete_role_in_use_409(self, admin_client, db):
        _seed_system_roles(db)
        db.add(Role(name="used_r", label="Used", tier=1, is_system=False,
                    is_manager=False, is_role_admin=False, capacities=[]))
        db.commit()
        with patch("src.routes.roles_crud.get_users_with_role", new_callable=AsyncMock) as m_users:
            m_users.return_value = [{"id": "some-user"}]
            resp = admin_client.delete("/roles/used_r")
        assert resp.status_code == 409
        assert resp.json()["detail"] == "role_in_use"

    def test_cascade_delete_reserved_to_presidence_admin(self, codir_client, db):
        _seed_system_roles(db)
        db.add(Role(name="used_r2", label="Used2", tier=1, is_system=False,
                    is_manager=False, is_role_admin=False, capacities=[]))
        db.commit()
        with patch("src.routes.roles_crud.get_users_with_role", new_callable=AsyncMock) as m_users:
            m_users.return_value = [{"id": "u1"}]
            resp = codir_client.delete("/roles/used_r2?cascade=true")
        assert resp.status_code == 403
