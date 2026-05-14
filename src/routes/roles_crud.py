from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from src.core.keycloak import require_role_admin, validate_jwt
from src.core.keycloak_admin import (
    create_realm_role, delete_realm_role, get_users_with_role, update_realm_role,
)
from src.crud.crud_role import (
    create_role, delete_role, get_role_by_name, get_roles_for_names, list_roles, update_role,
)
from src.database.session import get_db
from src.schemas.role import RoleCreate, RoleResponse, RoleUpdate
from src.utils.logger import logger

router = APIRouter(prefix="/roles", tags=["Roles Management"])


def _check_self_destruction(caller_roles_in_token: list[str], target_role_name: str, db: Session) -> None:
    caller_admin_roles = get_roles_for_names(db, caller_roles_in_token)
    role_admin_names = {r.name for r in caller_admin_roles if r.is_role_admin}
    if role_admin_names == {target_role_name}:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="self_destruction_forbidden")


def _caller_has_cascade_authority(roles_in_token: list[str]) -> bool:
    return bool({"presidence", "admin"}.intersection(roles_in_token))


@router.get("", response_model=list[RoleResponse])
def get_roles(
    db: Session = Depends(get_db),
    _: dict = Depends(validate_jwt),
):
    return list_roles(db)


@router.post("", response_model=RoleResponse, status_code=status.HTTP_201_CREATED)
async def create_custom_role(
    body: RoleCreate,
    payload: dict = Depends(require_role_admin),
    db: Session = Depends(get_db),
):
    caller_roles = payload.get("realm_access", {}).get("roles", [])
    caller_db_roles = get_roles_for_names(db, caller_roles)
    caller_max_tier = max((r.tier for r in caller_db_roles), default=-1)

    if body.tier > caller_max_tier:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                            detail="Vous ne pouvez pas créer un rôle à un tier supérieur au vôtre")

    if get_role_by_name(db, body.name):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT,
                            detail=f"Un rôle '{body.name}' existe déjà")

    await create_realm_role(body.name, body.label)
    role = create_role(db, name=body.name, label=body.label, tier=body.tier,
                       is_manager=body.is_manager, is_role_admin=body.is_role_admin,
                       capacities=body.capacities)
    logger.info(f"Rôle custom '{body.name}' créé par {payload.get('sub')}")
    return role


@router.put("/{role_name}", response_model=RoleResponse)
async def edit_role(
    role_name: str,
    body: RoleUpdate,
    payload: dict = Depends(require_role_admin),
    db: Session = Depends(get_db),
):
    role = get_role_by_name(db, role_name)
    if not role:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Rôle '{role_name}' introuvable")

    caller_roles = payload.get("realm_access", {}).get("roles", [])
    caller_db_roles = get_roles_for_names(db, caller_roles)
    caller_max_tier = max((r.tier for r in caller_db_roles), default=-1)
    if role.tier > caller_max_tier:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                            detail="Tier insuffisant pour modifier ce rôle")

    update_dict = body.model_dump(exclude_unset=True)
    if role.is_system:
        # System roles: only label is editable
        update_dict = {k: v for k, v in update_dict.items() if k == "label"}
    if "label" in update_dict:
        await update_realm_role(role_name, update_dict["label"])
    if update_dict:
        updated = update_role(db, role, RoleUpdate(**update_dict))
    else:
        updated = role

    logger.info(f"Rôle '{role_name}' mis à jour par {payload.get('sub')}")
    return updated


@router.delete("/{role_name}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_role(
    role_name: str,
    cascade: bool = Query(default=False),
    payload: dict = Depends(require_role_admin),
    db: Session = Depends(get_db),
):
    role = get_role_by_name(db, role_name)
    if not role:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Rôle '{role_name}' introuvable")

    if role.is_system:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="system_role_not_deletable")

    caller_roles = payload.get("realm_access", {}).get("roles", [])
    _check_self_destruction(caller_roles, role_name, db)

    users_with_role = await get_users_with_role(role_name)
    if users_with_role:
        if not cascade:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="role_in_use")
        if not _caller_has_cascade_authority(caller_roles):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                                detail="Cascade delete réservé à la Présidence et à l'Administrateur système")

    await delete_realm_role(role_name)
    delete_role(db, role)
    logger.info(f"Rôle '{role_name}' supprimé par {payload.get('sub')} (cascade={cascade})")
