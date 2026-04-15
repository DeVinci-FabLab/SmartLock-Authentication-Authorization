from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from src.core.keycloak import ROLE_ADMIN, require_admin, require_codir, require_locker_client
from src.core.keycloak_admin import (
    add_role_to_user,
    find_user_by_card_id,
    get_user_effective_roles,
    remove_role_from_user,
)
from src.crud.crud_access_log import create_access_log
from src.database.session import get_db
from src.models.locker_permission import Locker_Permission
from src.schemas.access_log import AccessLogCreate
from src.utils.logger import logger

router = APIRouter(
    prefix="/auth",
    tags=["Authentication & Hardware"],
)


class LockerCheckRequest(BaseModel):
    card_id: str


class LockerCheckResponse(BaseModel):
    allowed: bool
    display_name: str | None = None
    reason: str | None = None
    permissions: dict | None = None


def _is_expired(valid_until: str | None, now: datetime) -> bool:
    """Check if a permission is expired by parsing the ISO date string."""
    if not valid_until:
        return False
    try:
        expiry = datetime.fromisoformat(valid_until)
        if expiry.tzinfo is None:
            expiry = expiry.replace(tzinfo=timezone.utc)
        return expiry <= now
    except (ValueError, TypeError):
        logger.warning(f"Format valid_until invalide: {valid_until}")
        return False


@router.post(
    "/locker/{locker_id}/check",
    response_model=LockerCheckResponse,
)
async def check_locker_access(
    locker_id: int,
    request: LockerCheckRequest,
    db: Session = Depends(get_db),
    _: dict = Depends(require_locker_client),
):
    """
    Endpoint appele par le Raspberry Pi lors du scan d'un badge NFC.
    Verifie l'identite du badge via Keycloak, calcule les permissions,
    enregistre l'historique d'acces et renvoie la decision d'ouverture.
    """
    card_id = request.card_id
    logger.info(
        f"Demande d'acces au casier {locker_id} avec la carte {card_id}"
    )

    # 1. Identifier l'utilisateur dans Keycloak via son card_id
    try:
        user = await find_user_by_card_id(card_id)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erreur Keycloak (find_user_by_card_id): {e}")
        log_entry = AccessLogCreate(
            locker_id=locker_id,
            card_id=card_id,
            result="denied",
            reason="keycloak_error",
        )
        create_access_log(db, log_entry)
        return LockerCheckResponse(
            allowed=False, reason="keycloak_error"
        )

    if not user:
        logger.warning(f"Carte {card_id} non enregistree dans Keycloak.")
        log_entry = AccessLogCreate(
            locker_id=locker_id,
            card_id=card_id,
            result="denied",
            reason="card_not_registered",
        )
        create_access_log(db, log_entry)
        return LockerCheckResponse(
            allowed=False, reason="card_not_registered"
        )

    user_id = user["id"]
    display_name = (
        f"{user.get('firstName', '')} {user.get('lastName', '')}".strip()
        or user.get("username", "Utilisateur inconnu")
    )
    logger.debug(
        f"Utilisateur identifie : {display_name} (ID: {user_id})"
    )

    # 2. Recuperer les roles Keycloak de l'utilisateur
    try:
        roles = await get_user_effective_roles(user_id)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erreur Keycloak (get_user_effective_roles): {e}")
        log_entry = AccessLogCreate(
            locker_id=locker_id,
            card_id=card_id,
            user_id=user_id,
            username=display_name,
            result="denied",
            reason="keycloak_error",
        )
        create_access_log(db, log_entry)
        return LockerCheckResponse(
            allowed=False,
            display_name=display_name,
            reason="keycloak_error",
        )

    # 3. Recuperer les permissions pour ce casier
    try:
        locker_permissions = (
            db.query(Locker_Permission)
            .filter(Locker_Permission.locker_id == locker_id)
            .all()
        )
    except Exception as e:
        logger.error(f"Erreur DB (locker_permissions): {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erreur base de donnees",
        )

    # 4. Consolider les permissions
    granted = {
        "can_view": False,
        "can_open": False,
        "can_edit": False,
        "can_take": False,
        "can_manage": False,
    }
    has_permission_row = False
    now = datetime.now(timezone.utc)

    for perm in locker_permissions:
        if _is_expired(perm.valid_until, now):
            continue

        if perm.subject_type == "role" and perm.role_name in roles:
            has_permission_row = True
            granted["can_view"] |= perm.can_view
            granted["can_open"] |= perm.can_open
            granted["can_edit"] |= perm.can_edit
            granted["can_take"] |= perm.can_take
            granted["can_manage"] |= perm.can_manage

    # 5. Surcharge user-specific (ecrase les permissions role)
    user_perm = next(
        (
            p
            for p in locker_permissions
            if p.subject_type == "user" and p.user_id == user_id
        ),
        None,
    )

    if user_perm and not _is_expired(user_perm.valid_until, now):
        has_permission_row = True
        granted = {
            "can_view": user_perm.can_view,
            "can_open": user_perm.can_open,
            "can_edit": user_perm.can_edit,
            "can_take": user_perm.can_take,
            "can_manage": user_perm.can_manage,
        }

    # 6. Decision finale
    allowed = has_permission_row and granted["can_open"]
    reason = None if allowed else "no_permission"

    # 7. Historiser la decision
    log_entry = AccessLogCreate(
        locker_id=locker_id,
        card_id=card_id,
        user_id=user_id,
        username=display_name,
        result="allowed" if allowed else "denied",
        reason=reason,
        can_open=granted.get("can_open"),
        can_view=granted.get("can_view"),
    )
    create_access_log(db, log_entry)

    # 8. Repondre au Raspberry Pi
    if allowed:
        logger.info(
            f"Acces AUTORISE au casier {locker_id} pour {display_name}"
        )
        return LockerCheckResponse(
            allowed=True,
            display_name=display_name,
            permissions=granted,
        )
    else:
        logger.info(
            f"Acces REFUSE au casier {locker_id} "
            f"pour {display_name} (Raison: {reason})"
        )
        return LockerCheckResponse(
            allowed=False,
            display_name=display_name,
            reason=reason,
        )


# -------------------------------------------------------------------
# Élévation temporaire : codir → admin
# -------------------------------------------------------------------


@router.post(
    "/elevate",
    summary="Codir s'attribue temporairement le rôle admin",
)
async def elevate_to_admin(
    payload: dict = Depends(require_codir),
):
    """
    Permet à un membre du codir de s'attribuer temporairement le rôle admin.
    Le rôle admin est ajouté directement sur l'utilisateur dans Keycloak.
    Pour retirer le rôle, utiliser POST /auth/revoke-admin.
    """
    user_id = payload["sub"]
    roles = payload.get("realm_access", {}).get("roles", [])

    if ROLE_ADMIN in roles:
        return {"message": "Vous disposez déjà du rôle admin."}

    await add_role_to_user(user_id, ROLE_ADMIN)
    logger.info(f"Élévation admin accordée au codir {user_id}")
    return {"message": "Rôle admin accordé temporairement. Reconnectez-vous pour l'activer."}


# -------------------------------------------------------------------
# Révocation : admin renonce à son rôle admin
# -------------------------------------------------------------------


@router.post(
    "/revoke-admin",
    summary="Un admin renonce à son rôle admin",
)
async def revoke_admin(
    payload: dict = Depends(require_admin),
):
    """
    Permet à un administrateur de retirer son propre rôle admin.
    Utilisé par les codirs qui se sont élevés temporairement.
    """
    user_id = payload["sub"]
    await remove_role_from_user(user_id, ROLE_ADMIN)
    logger.info(f"Rôle admin révoqué pour l'utilisateur {user_id}")
    return {"message": "Rôle admin révoqué. Reconnectez-vous pour l'appliquer."}
