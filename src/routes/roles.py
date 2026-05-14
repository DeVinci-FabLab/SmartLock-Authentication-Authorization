from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from src.core.keycloak import validate_jwt
from src.core.keycloak_admin import add_role_to_user, remove_role_from_user
from src.crud.crud_role import get_role_by_name, get_roles_for_names
from src.database.session import get_db
from src.utils.logger import logger

router = APIRouter(prefix="/users", tags=["Role Management"])


def _check_can_manage_role(
    caller_roles_in_token: list[str],
    target_role_name: str,
    db: Session,
) -> None:
    """
    Raise 403 if caller cannot manage target role.
    Rule: caller must have is_manager=True AND tier > target.tier.
    Special case: T5 caller can manage another T5 (no tier above T5).
    """
    target = get_role_by_name(db, target_role_name)
    if not target:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail=f"Rôle '{target_role_name}' inconnu")

    caller_db_roles = get_roles_for_names(db, caller_roles_in_token)
    can_manage = any(
        r.is_manager and (r.tier > target.tier or (r.tier == 5 and target.tier == 5))
        for r in caller_db_roles
    )
    if not can_manage:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                            detail="insufficient_authority")


@router.post(
    "/{user_id}/roles/{role_name}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Attribuer un rôle à un utilisateur",
)
async def assign_role(
    user_id: str,
    role_name: str,
    payload: dict = Depends(validate_jwt),
    db: Session = Depends(get_db),
):
    caller_roles = payload.get("realm_access", {}).get("roles", [])
    _check_can_manage_role(caller_roles, role_name, db)
    try:
        await add_role_to_user(user_id, role_name)
    except HTTPException as e:
        if e.status_code == 409:
            return  # Already has role — silent no-op per CDC
        raise
    logger.info(f"Rôle '{role_name}' attribué à {user_id} par {payload.get('sub')}")


@router.delete(
    "/{user_id}/roles/{role_name}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Révoquer un rôle d'un utilisateur",
)
async def revoke_role(
    user_id: str,
    role_name: str,
    payload: dict = Depends(validate_jwt),
    db: Session = Depends(get_db),
):
    caller_roles = payload.get("realm_access", {}).get("roles", [])
    _check_can_manage_role(caller_roles, role_name, db)
    await remove_role_from_user(user_id, role_name)
    logger.info(f"Rôle '{role_name}' révoqué de {user_id} par {payload.get('sub')}")
