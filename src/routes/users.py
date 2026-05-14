from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status

from src.core.keycloak import (
    require_admin,
    require_lifecycle_admin,
    require_lifecycle_manager,
)
from src.core.keycloak_admin import (
    delete_keycloak_user,
    get_user,
    get_user_roles,
    list_groups,
    list_users,
    set_user_enabled,
)
from src.utils.logger import logger

# Toutes ces routes sont strictement réservées aux administrateurs
# La gestion des utilisateurs (création, modification, assignation de groupes/badges)
# se fait exclusivement via l'interface Keycloak.
router = APIRouter(
    tags=["User Management (Keycloak)"], dependencies=[Depends(require_admin)]
)


# --- Routes Utilisateurs (lecture seule) ---


@router.get("/users")
async def get_all_users(
    search: Optional[str] = Query(
        None, description="Recherche par nom, email ou username"
    ),
    first: int = 0,
    max_results: int = 100,
):
    """Liste les utilisateurs depuis Keycloak."""
    return await list_users(search=search, first=first, max_results=max_results)


@router.get("/users/{user_id}")
async def get_user_detail(user_id: str):
    """Retourne les informations complètes d'un utilisateur Keycloak par son UUID."""
    return await get_user(user_id)


@router.get("/users/{user_id}/roles")
async def get_user_role_list(user_id: str):
    """Liste les noms des rôles realm directement assignés à l'utilisateur."""
    return await get_user_roles(user_id)


# --- Routes Groupes (lecture seule) ---


@router.get("/groups")
async def get_all_groups():
    """Liste tous les groupes disponibles dans Keycloak."""
    return await list_groups()


# --- Routes Cycle de vie utilisateur ---

lifecycle_router = APIRouter(tags=["User Lifecycle"])


@lifecycle_router.post(
    "/users/{user_id}/revoke",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Révoquer un compte utilisateur (désactiver dans Keycloak)",
)
async def revoke_user(
    user_id: str,
    payload: dict = Depends(require_lifecycle_manager),
):
    if user_id == payload.get("sub"):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="self_revocation_forbidden")
    await set_user_enabled(user_id, False)
    logger.info(f"Compte {user_id} révoqué par {payload.get('sub')}")


@lifecycle_router.post(
    "/users/{user_id}/restore",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Restaurer un compte révoqué",
)
async def restore_user(
    user_id: str,
    payload: dict = Depends(require_lifecycle_manager),
):
    if user_id == payload.get("sub"):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="self_restore_forbidden")
    await set_user_enabled(user_id, True)
    logger.info(f"Compte {user_id} restauré par {payload.get('sub')}")


@lifecycle_router.delete(
    "/users/{user_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Supprimer définitivement un compte utilisateur",
)
async def delete_user(
    user_id: str,
    payload: dict = Depends(require_lifecycle_admin),
):
    await delete_keycloak_user(user_id)
    logger.info(f"Compte {user_id} supprimé définitivement par {payload.get('sub')}")
