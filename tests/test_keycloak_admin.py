import pytest
from unittest.mock import AsyncMock, patch, MagicMock
import httpx

pytestmark = pytest.mark.anyio


async def test_set_user_enabled_calls_put():
    mock_resp = MagicMock()
    mock_resp.raise_for_status = MagicMock()
    with patch("src.core.keycloak_admin.get_admin_token", new_callable=AsyncMock) as m_tok, \
         patch("httpx.AsyncClient") as m_client:
        m_tok.return_value = "fake-token"
        m_client.return_value.__aenter__.return_value.put = AsyncMock(return_value=mock_resp)
        from src.core.keycloak_admin import set_user_enabled
        await set_user_enabled("user-1", True)
        m_client.return_value.__aenter__.return_value.put.assert_called_once()


async def test_delete_keycloak_user_calls_delete():
    mock_resp = MagicMock()
    mock_resp.raise_for_status = MagicMock()
    with patch("src.core.keycloak_admin.get_admin_token", new_callable=AsyncMock) as m_tok, \
         patch("httpx.AsyncClient") as m_client:
        m_tok.return_value = "fake-token"
        m_client.return_value.__aenter__.return_value.delete = AsyncMock(return_value=mock_resp)
        from src.core.keycloak_admin import delete_keycloak_user
        await delete_keycloak_user("user-1")
        m_client.return_value.__aenter__.return_value.delete.assert_called_once()


async def test_create_realm_role_calls_post():
    mock_resp = MagicMock()
    mock_resp.raise_for_status = MagicMock()
    with patch("src.core.keycloak_admin.get_admin_token", new_callable=AsyncMock) as m_tok, \
         patch("httpx.AsyncClient") as m_client:
        m_tok.return_value = "fake-token"
        m_client.return_value.__aenter__.return_value.post = AsyncMock(return_value=mock_resp)
        from src.core.keycloak_admin import create_realm_role
        await create_realm_role("new_role", "New Role Description")
        m_client.return_value.__aenter__.return_value.post.assert_called_once()
