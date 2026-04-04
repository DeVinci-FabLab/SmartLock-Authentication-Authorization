from datetime import datetime, timezone

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from src.core.keycloak import require_locker_client
from src.core.keycloak_admin import find_user_by_card_id, get_user_effective_roles
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


@router.post("/locker/{locker_id}/check", response_model=LockerCheckResponse)
async def check_locker_access(
    locker_id: int,
    request: LockerCheckRequest,
    db: Session = Depends(get_db),
    # Réservé au Raspberry Pi (client smartlock-lockers)
    _: dict = Depends(require_locker_client),
):
    """
    Endpoint appelé par le Raspberry Pi lors du scan d'un badge NFC.
    Vérifie l'identité du badge via Keycloak, calcule les permissions,
    enregistre l'historique d'accès et renvoie la décision d'ouverture.
    """
    card_id = request.card_id
    logger.info(f"Demande d'accès au casier {locker_id} avec la carte {card_id}")

    # 1. Identifier l'utilisateur dans Keycloak via son card_id
    user = await find_user_by_card_id(card_id)

    if not user:
        logger.warning(f"Carte {card_id} non enregistrée dans Keycloak.")
        # Historiser le refus
        log_entry = AccessLogCreate(
            locker_id=locker_id,
            card_id=card_id,
            result="denied",
            reason="card_not_registered",
        )
        create_access_log(db, log_entry)
        return LockerCheckResponse(allowed=False, reason="card_not_registered")

    user_id = user["id"]
    display_name = (
        f"{user.get('firstName', '')} {user.get('lastName', '')}".strip()
        or user.get("username", "Utilisateur inconnu")
    )
    logger.debug(f"Utilisateur identifié : {display_name} (ID: {user_id})")

    # 2. Récupérer les rôles Keycloak de l'utilisateur
    roles = await get_user_effective_roles(user_id)

    # 3. Récupérer toutes les permissions pour ce casier depuis la base de données
    locker_permissions = (
        db.query(Locker_Permission)
        .filter(Locker_Permission.locker_id == locker_id)
        .all()
    )

    # Variables pour consolider les permissions accordées
    granted_permissions = {
        "can_view": False,
        "can_open": False,
        "can_edit": False,
        "can_take": False,
        "can_manage": False,
    }

    has_permission_row = False
    now_iso = datetime.now(timezone.utc).isoformat()

    # 4. Parcourir les permissions applicables
    for perm in locker_permissions:
        # Vérifier l'expiration
        if perm.valid_until and perm.valid_until < now_iso:
            continue

        # Permission basée sur un rôle que l'utilisateur possède
        if perm.subject_type == "role" and perm.role_name in roles:
            has_permission_row = True
            # Fusion OR (un rôle suffit)
            granted_permissions["can_view"] |= perm.can_view
            granted_permissions["can_open"] |= perm.can_open
            granted_permissions["can_edit"] |= perm.can_edit
            granted_permissions["can_take"] |= perm.can_take
            granted_permissions["can_manage"] |= perm.can_manage

    # 5. Surcharge user-specific (écrase les permissions rôle)
    user_specific_perm = next(
        (
            p
            for p in locker_permissions
            if p.subject_type == "user" and p.user_id == user_id
        ),
        None,
    )

    if user_specific_perm:
        if user_specific_perm.valid_until and user_specific_perm.valid_until < now_iso:
            # La permission spécifique est expirée, on garde les permissions des rôles
            pass
        else:
            has_permission_row = True
            granted_permissions = {
                "can_view": user_specific_perm.can_view,
                "can_open": user_specific_perm.can_open,
                "can_edit": user_specific_perm.can_edit,
                "can_take": user_specific_perm.can_take,
                "can_manage": user_specific_perm.can_manage,
            }

    # 6. Décision finale
    allowed = has_permission_row and granted_permissions["can_open"]
    reason = None if allowed else "no_permission"

    # 7. Historiser la décision
    log_entry = AccessLogCreate(
        locker_id=locker_id,
        card_id=card_id,
        user_id=user_id,
        username=display_name,
        result="allowed" if allowed else "denied",
        reason=reason,
        can_open=granted_permissions.get("can_open"),
        can_view=granted_permissions.get("can_view"),
    )
    create_access_log(db, log_entry)

    # 8. Répondre au Raspberry Pi
    if allowed:
        logger.info(f"Accès AUTORISÉ au casier {locker_id} pour {display_name}")
        return LockerCheckResponse(
            allowed=True, display_name=display_name, permissions=granted_permissions
        )
    else:
        logger.info(
            f"Accès REFUSÉ au casier {locker_id} pour {display_name} (Raison: {reason})"
        )
        return LockerCheckResponse(
            allowed=False, display_name=display_name, reason=reason
        )
