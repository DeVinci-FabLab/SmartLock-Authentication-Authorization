from fastapi import APIRouter, Depends, HTTPException, status

from src.core.keycloak import (
    ROLE_CODIR,
    ROLES_MANAGED_BY_ADMIN_ONLY,
    ROLES_MANAGED_BY_CODIR,
    ROLES_MANAGED_BY_MATERIALISTE,
    ROLE_ADMIN,
    ROLE_MATERIALISTE,
    require_materialiste_or_above,
    validate_jwt,
)
from src.core.keycloak_admin import add_role_to_user, remove_role_from_user
from src.utils.logger import logger

router = APIRouter(
    prefix="/users",
    tags=["Role Management"],
)

# Permission map: role_name → minimum set of roles allowed to manage it
_ROLE_MANAGER_MAP: dict[str, set[str]] = {
    **{r: {ROLE_MATERIALISTE, ROLE_CODIR, ROLE_ADMIN} for r in ROLES_MANAGED_BY_MATERIALISTE},
    **{r: {ROLE_CODIR, ROLE_ADMIN} for r in ROLES_MANAGED_BY_CODIR},
    **{r: {ROLE_ADMIN} for r in ROLES_MANAGED_BY_ADMIN_ONLY},
}


def _check_can_manage_role(requester_roles: list[str], target_role: str) -> None:
    """Raise 403 if the requester cannot manage the target role."""
    allowed = _ROLE_MANAGER_MAP.get(target_role)
    if allowed is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Rôle '{target_role}' inconnu ou non gérable via cette API.",
        )
    if not allowed.intersection(requester_roles):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Vous n'avez pas le droit de gérer le rôle '{target_role}'.",
        )


@router.post(
    "/{user_id}/roles/{role_name}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Attribuer un rôle à un utilisateur",
)
async def assign_role(
    user_id: str,
    role_name: str,
    payload: dict = Depends(require_materialiste_or_above),
):
    """
    Attribue un rôle realm Keycloak à un utilisateur.

    Permissions requises selon le rôle cible :
    - membre, 3d       → matérialiste, codir, admin
    - electronique, textile, materialiste, admin → codir, admin
    - codir            → admin uniquement
    """
    requester_roles = payload.get("realm_access", {}).get("roles", [])
    _check_can_manage_role(requester_roles, role_name)

    await add_role_to_user(user_id, role_name)
    logger.info(
        f"Rôle '{role_name}' attribué à {user_id} par {payload.get('sub')}"
    )


@router.delete(
    "/{user_id}/roles/{role_name}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Révoquer un rôle d'un utilisateur",
)
async def revoke_role(
    user_id: str,
    role_name: str,
    payload: dict = Depends(require_materialiste_or_above),
):
    """
    Retire un rôle realm Keycloak d'un utilisateur.

    Permissions requises selon le rôle cible :
    - membre, 3d       → matérialiste, codir, admin
    - electronique, textile, materialiste, admin → codir, admin
    - codir            → admin uniquement
    """
    requester_roles = payload.get("realm_access", {}).get("roles", [])
    _check_can_manage_role(requester_roles, role_name)

    await remove_role_from_user(user_id, role_name)
    logger.info(
        f"Rôle '{role_name}' révoqué de {user_id} par {payload.get('sub')}"
    )
