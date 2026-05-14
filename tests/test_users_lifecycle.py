import pytest
from unittest.mock import AsyncMock, patch

pytestmark = pytest.mark.anyio


class TestUserLifecycle:
    def test_revoke_requires_lifecycle_manager(self, membre_client):
        resp = membre_client.post("/users/user-1/revoke")
        assert resp.status_code == 403

    def test_revoke_ok_for_codir(self, codir_client):
        with patch("src.routes.users.set_user_enabled", new_callable=AsyncMock) as m:
            resp = codir_client.post("/users/user-1/revoke")
        assert resp.status_code == 204
        m.assert_called_once_with("user-1", False)

    def test_restore_ok_for_admin(self, admin_client):
        with patch("src.routes.users.set_user_enabled", new_callable=AsyncMock) as m:
            resp = admin_client.post("/users/user-1/restore")
        assert resp.status_code == 204
        m.assert_called_once_with("user-1", True)

    def test_delete_requires_lifecycle_admin(self, codir_client):
        resp = codir_client.delete("/users/user-1")
        assert resp.status_code == 403

    def test_delete_ok_for_admin(self, admin_client):
        with patch("src.routes.users.delete_keycloak_user", new_callable=AsyncMock) as m:
            resp = admin_client.delete("/users/user-1")
        assert resp.status_code == 204
        m.assert_called_once_with("user-1")
