from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from src.core.keycloak import require_locker_client
from src.utils.card_hash import hash_card_id
from src.core.keycloak_admin import find_user_by_card_id, get_user_effective_roles
from src.crud.crud_access_log import create_access_log
from src.database.session import get_db
from src.models.locker_permission import Locker_Permission, PERMISSION_ORDER
from src.schemas.access_log import AccessLogCreate
from src.utils.logger import logger

router = APIRouter(prefix="/auth", tags=["Authentication & Hardware"])


class LockerCheckRequest(BaseModel):
    card_id: str


class LockerCheckResponse(BaseModel):
    allowed: bool
    display_name: str | None = None
    reason: str | None = None
    permissions: dict | None = None


def _is_expired(valid_until: str | None, now: datetime) -> bool:
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


def _effective_permission(role_permissions: list[Locker_Permission], now: datetime) -> str | None:
    """Return the highest permission_level among non-expired role entries, or None."""
    best: str | None = None
    for perm in role_permissions:
        if _is_expired(perm.valid_until, now):
            continue
        if best is None or PERMISSION_ORDER[perm.permission_level] > PERMISSION_ORDER[best]:
            best = perm.permission_level
    return best


@router.post("/locker/{locker_id}/check", response_model=LockerCheckResponse)
async def check_locker_access(
    locker_id: int,
    request: LockerCheckRequest,
    db: Session = Depends(get_db),
    _: dict = Depends(require_locker_client),
):
    card_id = hash_card_id(request.card_id)
    logger.info(f"Demande d'accès au casier {locker_id} avec la carte {card_id}")

    # 1. Find user in Keycloak by card_id
    try:
        user = await find_user_by_card_id(card_id)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erreur Keycloak (find_user_by_card_id): {e}")
        create_access_log(db, AccessLogCreate(locker_id=locker_id, card_id=card_id,
                                               result="denied", reason="keycloak_error"))
        return LockerCheckResponse(allowed=False, reason="keycloak_error")

    if not user:
        logger.warning(f"Carte {card_id} non enregistrée dans Keycloak.")
        create_access_log(db, AccessLogCreate(locker_id=locker_id, card_id=card_id,
                                               result="denied", reason="card_not_registered"))
        return LockerCheckResponse(allowed=False, reason="card_not_registered")

    # 2. Check account is active (divergence #10)
    if not user.get("enabled", True):
        user_id = user["id"]
        display_name = (f"{user.get('firstName','')} {user.get('lastName','')}".strip()
                        or user.get("username", "Utilisateur inconnu"))
        create_access_log(db, AccessLogCreate(locker_id=locker_id, card_id=card_id,
                                               user_id=user_id, username=display_name,
                                               result="denied", reason="account_revoked"))
        return LockerCheckResponse(allowed=False, display_name=display_name, reason="account_revoked")

    user_id = user["id"]
    display_name = (f"{user.get('firstName','')} {user.get('lastName','')}".strip()
                    or user.get("username", "Utilisateur inconnu"))

    # 3. Get user roles from Keycloak
    try:
        roles = await get_user_effective_roles(user_id)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erreur Keycloak (get_user_effective_roles): {e}")
        create_access_log(db, AccessLogCreate(locker_id=locker_id, card_id=card_id,
                                               user_id=user_id, username=display_name,
                                               result="denied", reason="keycloak_error"))
        return LockerCheckResponse(allowed=False, display_name=display_name, reason="keycloak_error")

    # 4. Get locker permissions and consolidate
    try:
        locker_permissions = (db.query(Locker_Permission)
                              .filter(Locker_Permission.locker_id == locker_id)
                              .filter(Locker_Permission.role_name.in_(roles))
                              .all())
    except Exception as e:
        logger.error(f"Erreur DB (locker_permissions): {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Erreur base de données")

    now = datetime.now(timezone.utc)
    best_level = _effective_permission(locker_permissions, now)

    # 5. Decision: can_open or higher grants access
    allowed = best_level is not None and PERMISSION_ORDER[best_level] >= PERMISSION_ORDER["can_open"]
    reason = None if allowed else "no_permission"

    # 6. Audit log
    create_access_log(db, AccessLogCreate(
        locker_id=locker_id, card_id=card_id,
        user_id=user_id, username=display_name,
        result="allowed" if allowed else "denied", reason=reason,
        can_open=allowed,
        can_view=best_level is not None,
    ))

    if allowed:
        logger.info(f"Accès AUTORISÉ au casier {locker_id} pour {display_name}")
        return LockerCheckResponse(allowed=True, display_name=display_name,
                                   permissions={"permission_level": best_level})
    else:
        logger.info(f"Accès REFUSÉ au casier {locker_id} pour {display_name} (Raison: {reason})")
        return LockerCheckResponse(allowed=False, display_name=display_name, reason=reason)
