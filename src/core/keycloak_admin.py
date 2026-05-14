"""
Keycloak Admin REST API client (lecture seule)
===============================================
Utilisé par l'API (service account smartlock-api) pour :
- Rechercher un utilisateur par card_id
- Récupérer ses rôles effectifs (directs + hérités des groupes parents)
- Lister les utilisateurs et les groupes

La création et la modification des utilisateurs, groupes et badges
se font exclusivement via l'interface Keycloak.

Toutes les fonctions sont async et utilisent httpx.AsyncClient.
Le token service account est mis en cache jusqu'à 30s avant son expiration.
"""

import time

import httpx
from fastapi import HTTPException, status

from src.core.config import settings
from src.utils.logger import logger

# ── Cache du token service account ────────────────────────────────────────────
_token_cache: dict = {"access_token": None, "expires_at": 0.0}


# ── Helpers ────────────────────────────────────────────────────────────────────


def _admin_base() -> str:
    return f"{settings.KEYCLOAK_URL}/admin/realms/{settings.KEYCLOAK_REALM}"


def _token_url() -> str:
    return (
        f"{settings.KEYCLOAK_URL}/realms/{settings.KEYCLOAK_REALM}"
        "/protocol/openid-connect/token"
    )


def _auth_headers(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def _handle_keycloak_error(e: httpx.HTTPStatusError, context: str) -> None:
    """Convertit les erreurs Keycloak en HTTPException FastAPI lisibles."""
    logger.error(
        f"Keycloak error [{context}] : {e.response.status_code} — {e.response.text}"
    )
    if e.response.status_code == 401:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Service d'authentification indisponible"
            " (token service account invalide)",
        )
    if e.response.status_code == 404:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Ressource Keycloak introuvable ({context})",
        )
    if e.response.status_code == 409:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Conflit Keycloak ({context})",
        )
    raise HTTPException(
        status_code=status.HTTP_502_BAD_GATEWAY,
        detail=f"Erreur Keycloak inattendue ({context})",
    )


# ── Token service account ──────────────────────────────────────────────────────


async def get_admin_token() -> str:
    """
    Retourne un token valide pour le service account smartlock-api.
    Le token est mis en cache jusqu'à 30 secondes avant son expiration
    pour éviter les race conditions.
    """
    now = time.time()
    if _token_cache["access_token"] and now < _token_cache["expires_at"]:
        return _token_cache["access_token"]

    logger.debug("Renouvellement du token service account Keycloak...")
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                _token_url(),
                data={
                    "grant_type": "client_credentials",
                    "client_id": settings.KEYCLOAK_CLIENT_ID,
                    "client_secret": settings.KEYCLOAK_CLIENT_SECRET,
                },
            )
            resp.raise_for_status()
    except httpx.HTTPStatusError as e:
        logger.error(f"Impossible d'obtenir le token service account : {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Service d'authentification Keycloak indisponible",
        )
    except httpx.RequestError as e:
        logger.error(f"Keycloak injoignable : {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Keycloak injoignable",
        )

    data = resp.json()
    _token_cache["access_token"] = data["access_token"]
    _token_cache["expires_at"] = now + data["expires_in"] - 30

    logger.debug("Token service account Keycloak renouvelé avec succès")
    return _token_cache["access_token"]


# ── Lecture ────────────────────────────────────────────────────────────────────


async def find_user_by_card_id(card_id: str) -> dict | None:
    """
    Cherche un utilisateur Keycloak par son attribut custom card_id.
    Retourne le premier résultat ou None si introuvable.
    """
    token = await get_admin_token()
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"{_admin_base()}/users",
                params={"q": f"card_id:{card_id}"},
                headers=_auth_headers(token),
            )
            resp.raise_for_status()
    except httpx.HTTPStatusError as e:
        _handle_keycloak_error(e, "find_user_by_card_id")

    users = resp.json()
    if not users:
        logger.debug(f"Aucun utilisateur trouvé pour card_id={card_id}")
        return None

    logger.debug(f"Utilisateur trouvé : {users[0]['username']} (card_id={card_id})")
    return users[0]


async def get_user_effective_roles(user_id: str) -> list[str]:
    """
    Retourne les rôles effectifs d'un utilisateur.
    Utilise /composite pour inclure les rôles hérités des groupes parents.
    """
    token = await get_admin_token()
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"{_admin_base()}/users/{user_id}/role-mappings/realm/composite",
                headers=_auth_headers(token),
            )
            resp.raise_for_status()
    except httpx.HTTPStatusError as e:
        _handle_keycloak_error(e, "get_user_effective_roles")

    roles = [r["name"] for r in resp.json()]
    logger.debug(f"Rôles effectifs user={user_id} : {roles}")
    return roles


async def get_user_groups(user_id: str) -> list[dict]:
    """Retourne les groupes auxquels appartient un utilisateur."""
    token = await get_admin_token()
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"{_admin_base()}/users/{user_id}/groups",
                headers=_auth_headers(token),
            )
            resp.raise_for_status()
    except httpx.HTTPStatusError as e:
        _handle_keycloak_error(e, "get_user_groups")

    return resp.json()


async def list_groups() -> list[dict]:
    """Retourne la liste de tous les groupes du realm."""
    token = await get_admin_token()
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"{_admin_base()}/groups",
                headers=_auth_headers(token),
            )
            resp.raise_for_status()
    except httpx.HTTPStatusError as e:
        _handle_keycloak_error(e, "list_groups")

    return resp.json()


async def get_user(user_id: str) -> dict:
    """Retourne les informations complètes d'un utilisateur par son UUID."""
    token = await get_admin_token()
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"{_admin_base()}/users/{user_id}",
                headers=_auth_headers(token),
            )
            resp.raise_for_status()
    except httpx.HTTPStatusError as e:
        _handle_keycloak_error(e, "get_user")

    return resp.json()


async def list_users(
    search: str | None = None,
    first: int = 0,
    max_results: int = 100,
) -> list[dict]:
    """
    Liste les utilisateurs du realm.
    `search` filtre sur username, email, firstName, lastName.
    """
    token = await get_admin_token()
    params: dict = {"first": first, "max": max_results}
    if search:
        params["search"] = search

    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"{_admin_base()}/users",
                params=params,
                headers=_auth_headers(token),
            )
            resp.raise_for_status()
    except httpx.HTTPStatusError as e:
        _handle_keycloak_error(e, "list_users")

    return resp.json()


# ── Gestion des rôles ──────────────────────────────────────────────────────────


async def get_realm_role(role_name: str) -> dict:
    """
    Retourne la représentation d'un rôle realm par son nom.
    Nécessaire pour les opérations d'ajout/suppression de rôles.
    """
    token = await get_admin_token()
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"{_admin_base()}/roles/{role_name}",
                headers=_auth_headers(token),
            )
            resp.raise_for_status()
    except httpx.HTTPStatusError as e:
        _handle_keycloak_error(e, f"get_realm_role({role_name})")

    return resp.json()


async def add_role_to_user(user_id: str, role_name: str) -> None:
    """
    Ajoute un rôle realm à un utilisateur.
    Récupère d'abord la représentation du rôle, puis l'assigne.
    """
    role = await get_realm_role(role_name)
    token = await get_admin_token()
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"{_admin_base()}/users/{user_id}/role-mappings/realm",
                json=[{"id": role["id"], "name": role["name"]}],
                headers=_auth_headers(token),
            )
            resp.raise_for_status()
    except httpx.HTTPStatusError as e:
        _handle_keycloak_error(e, f"add_role_to_user({user_id}, {role_name})")

    logger.info(f"Rôle '{role_name}' ajouté à l'utilisateur {user_id}")


async def remove_role_from_user(user_id: str, role_name: str) -> None:
    """
    Retire un rôle realm d'un utilisateur.
    Récupère d'abord la représentation du rôle, puis le retire.
    """
    role = await get_realm_role(role_name)
    token = await get_admin_token()
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.request(
                "DELETE",
                f"{_admin_base()}/users/{user_id}/role-mappings/realm",
                json=[{"id": role["id"], "name": role["name"]}],
                headers=_auth_headers(token),
            )
            resp.raise_for_status()
    except httpx.HTTPStatusError as e:
        _handle_keycloak_error(e, f"remove_role_from_user({user_id}, {role_name})")

    logger.info(f"Rôle '{role_name}' retiré de l'utilisateur {user_id}")


# ── Gestion du cycle de vie des utilisateurs ──────────────────────────────────


async def set_user_enabled(user_id: str, enabled: bool) -> None:
    """Met à jour le flag enabled d'un utilisateur Keycloak (revoke / restore)."""
    token = await get_admin_token()
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.put(
                f"{_admin_base()}/users/{user_id}",
                json={"enabled": enabled},
                headers=_auth_headers(token),
            )
            resp.raise_for_status()
    except httpx.HTTPStatusError as e:
        _handle_keycloak_error(e, f"set_user_enabled({user_id}, {enabled})")
    logger.info(f"Utilisateur {user_id} — enabled={enabled}")


async def delete_keycloak_user(user_id: str) -> None:
    """Supprime définitivement un utilisateur de Keycloak (hard delete)."""
    token = await get_admin_token()
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.delete(
                f"{_admin_base()}/users/{user_id}",
                headers=_auth_headers(token),
            )
            resp.raise_for_status()
    except httpx.HTTPStatusError as e:
        _handle_keycloak_error(e, f"delete_keycloak_user({user_id})")
    logger.info(f"Utilisateur {user_id} supprimé définitivement de Keycloak")


# ── CRUD rôles Keycloak ────────────────────────────────────────────────────────


async def create_realm_role(name: str, description: str = "") -> None:
    """Crée un rôle realm dans Keycloak."""
    token = await get_admin_token()
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"{_admin_base()}/roles",
                json={"name": name, "description": description},
                headers=_auth_headers(token),
            )
            resp.raise_for_status()
    except httpx.HTTPStatusError as e:
        _handle_keycloak_error(e, f"create_realm_role({name})")
    logger.info(f"Rôle Keycloak '{name}' créé")


async def update_realm_role(name: str, new_description: str) -> None:
    """Met à jour la description d'un rôle realm Keycloak."""
    token = await get_admin_token()
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.put(
                f"{_admin_base()}/roles/{name}",
                json={"name": name, "description": new_description},
                headers=_auth_headers(token),
            )
            resp.raise_for_status()
    except httpx.HTTPStatusError as e:
        _handle_keycloak_error(e, f"update_realm_role({name})")


async def delete_realm_role(name: str) -> None:
    """Supprime un rôle realm de Keycloak."""
    token = await get_admin_token()
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.delete(
                f"{_admin_base()}/roles/{name}",
                headers=_auth_headers(token),
            )
            resp.raise_for_status()
    except httpx.HTTPStatusError as e:
        _handle_keycloak_error(e, f"delete_realm_role({name})")
    logger.info(f"Rôle Keycloak '{name}' supprimé")


async def get_users_with_role(role_name: str) -> list[dict]:
    """Retourne la liste des utilisateurs qui ont le rôle donné."""
    token = await get_admin_token()
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"{_admin_base()}/roles/{role_name}/users",
                headers=_auth_headers(token),
            )
            resp.raise_for_status()
            return resp.json()
    except httpx.HTTPStatusError as e:
        _handle_keycloak_error(e, f"get_users_with_role({role_name})")


async def get_user_roles(user_id: str) -> list[str]:
    """Retourne la liste des noms de rôles realm assignés directement à l'utilisateur."""
    token = await get_admin_token()
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"{_admin_base()}/users/{user_id}/role-mappings/realm",
                headers=_auth_headers(token),
            )
            resp.raise_for_status()
            return [r["name"] for r in resp.json()]
    except httpx.HTTPStatusError as e:
        _handle_keycloak_error(e, f"get_user_roles({user_id})")
