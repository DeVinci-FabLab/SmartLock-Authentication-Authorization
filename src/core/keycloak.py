"""
Keycloak integration
====================
- validate_jwt()                  : vérifie le Bearer JWT (admins ET service accounts)
- require_admin()                 : rôle 'admin' requis
- require_codir_or_admin()        : rôle 'codir' ou 'admin' requis
- require_materialiste_or_above() : rôle 'materialiste', 'codir' ou 'admin' requis
- require_codir()                 : rôle 'codir' requis (élévation temporaire)
- require_nfc_scanner()           : service account nfc-scanner
- require_locker_client()         : service account smartlock-lockers
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import httpx
from fastapi import Depends, HTTPException, Security, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt

from src.core.config import settings
from src.database.session import get_db
from src.utils.logger import logger

if TYPE_CHECKING:
    from sqlalchemy.orm import Session

bearer_scheme = HTTPBearer()

# ── Service account client IDs ─────────────────────────────────────────────────
NFC_SCANNER_CLIENT_ID = "nfc-scanner"
LOCKER_CLIENT_ID = "smartlock-lockers"

# ── Realm role constants ───────────────────────────────────────────────────────
ROLE_MEMBRE = "membre"
ROLE_3D = "3d"
ROLE_ELECTRONIQUE = "electronique"
ROLE_TEXTILE = "textile"
ROLE_MATERIALISTE = "materialiste"
ROLE_CODIR = "codir"
ROLE_ADMIN = "admin"

# Roles manageable by materialiste or above (give/revoke)
ROLES_MANAGED_BY_MATERIALISTE = {ROLE_MEMBRE, ROLE_3D}
# Roles manageable by codir or above (give/revoke)
ROLES_MANAGED_BY_CODIR = {ROLE_ELECTRONIQUE, ROLE_TEXTILE, ROLE_MATERIALISTE, ROLE_ADMIN}
# Roles manageable by admin only (give/revoke)
ROLES_MANAGED_BY_ADMIN_ONLY = {ROLE_CODIR}


def _jwks_uri() -> str:
    return (
        f"{settings.KEYCLOAK_URL}/realms/{settings.KEYCLOAK_REALM}"
        f"/protocol/openid-connect/certs"
    )


# -------------------------------------------------------------------
# Validation JWT générique (admins + service accounts)
# -------------------------------------------------------------------
async def validate_jwt(
    credentials: HTTPAuthorizationCredentials = Security(bearer_scheme),
) -> dict:
    """
    Valide le Bearer JWT émis par Keycloak.
    Fonctionne pour les tokens utilisateurs ET les tokens service account.
    Retourne le payload décodé.
    """
    token = credentials.credentials

    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(_jwks_uri())
            resp.raise_for_status()
            jwks = resp.json()

        payload = jwt.decode(
            token,
            jwks,
            algorithms=["RS256"],
            options={"verify_aud": False},
        )
        logger.debug(f"JWT valide — sub={payload.get('sub')} azp={payload.get('azp')}")
        return payload

    except JWTError as e:
        logger.warning(f"JWT invalide : {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token invalide ou expiré",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except httpx.HTTPError as e:
        logger.error(f"Impossible de joindre Keycloak : {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Service d'authentification indisponible",
        )


# -------------------------------------------------------------------
# Dependency : réservé au service account nfc-scanner
# -------------------------------------------------------------------
async def require_nfc_scanner(
    payload: dict = Depends(validate_jwt),
) -> dict:
    """
    Vérifie que le token appartient au service account nfc-scanner.
    Le champ 'azp' (authorized party) contient le client_id de l'émetteur.
    """
    azp = payload.get("azp", "")
    if azp != NFC_SCANNER_CLIENT_ID:
        logger.warning(f"Accès refusé — azp={azp} != {NFC_SCANNER_CLIENT_ID}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Accès réservé au module NFC",
        )
    return payload


# -------------------------------------------------------------------
# Dependency : réservé au client smartlock-lockers (Raspberry Pis)
# -------------------------------------------------------------------
async def require_locker_client(
    payload: dict = Depends(validate_jwt),
) -> dict:
    """
    Vérifie que le token appartient au client smartlock-lockers (les casiers physiques).
    """
    azp = payload.get("azp", "")
    if azp != LOCKER_CLIENT_ID:
        logger.warning(f"Accès refusé — azp={azp} != {LOCKER_CLIENT_ID}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Accès réservé aux terminaux physiques (casiers)",
        )
    return payload


# -------------------------------------------------------------------
# Dependency : réservé aux admins Keycloak
# -------------------------------------------------------------------
async def require_admin(
    payload: dict = Depends(validate_jwt),
) -> dict:
    """
    Vérifie que le token contient le rôle 'admin' dans realm_access.roles.
    """
    roles = payload.get("realm_access", {}).get("roles", [])
    if ROLE_ADMIN not in roles:
        logger.warning(f"Accès refusé — roles={roles}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Accès réservé aux administrateurs",
        )
    return payload


# -------------------------------------------------------------------
# Dependency : réservé aux codirs ET admins
# -------------------------------------------------------------------
async def require_codir_or_admin(
    payload: dict = Depends(validate_jwt),
) -> dict:
    """
    Vérifie que le token contient le rôle 'codir' ou 'admin'.
    Utilisé pour les opérations de gestion des rôles électronique, textile,
    matérialiste, admin et pour donner le rôle admin.
    """
    roles = payload.get("realm_access", {}).get("roles", [])
    if ROLE_CODIR not in roles and ROLE_ADMIN not in roles:
        logger.warning(f"Accès refusé — roles={roles}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Accès réservé aux codirs et administrateurs",
        )
    return payload


# -------------------------------------------------------------------
# Dependency : réservé aux matérialistes, codirs ET admins
# -------------------------------------------------------------------
async def require_materialiste_or_above(
    payload: dict = Depends(validate_jwt),
) -> dict:
    """
    Vérifie que le token contient le rôle 'materialiste', 'codir' ou 'admin'.
    Utilisé pour les opérations de gestion des rôles membre et 3d.
    """
    roles = payload.get("realm_access", {}).get("roles", [])
    if not {ROLE_MATERIALISTE, ROLE_CODIR, ROLE_ADMIN}.intersection(roles):
        logger.warning(f"Accès refusé — roles={roles}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Accès réservé aux matérialistes, codirs et administrateurs",
        )
    return payload


# -------------------------------------------------------------------
# Dependency : réservé aux codirs uniquement (élévation temporaire)
# -------------------------------------------------------------------
async def require_codir(
    payload: dict = Depends(validate_jwt),
) -> dict:
    """
    Vérifie que le token contient le rôle 'codir'.
    Utilisé pour l'auto-élévation au rôle admin (temporaire).
    """
    roles = payload.get("realm_access", {}).get("roles", [])
    if ROLE_CODIR not in roles:
        logger.warning(f"Accès refusé — roles={roles}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Accès réservé aux membres du codir",
        )
    return payload


# -------------------------------------------------------------------
# Dependency : réservé aux role admins (is_role_admin=True dans la DB)
# -------------------------------------------------------------------
async def require_role_admin(
    payload: dict = Depends(validate_jwt),
    db: "Session" = Depends(get_db),
) -> dict:
    """Requires caller to have at least one role with is_role_admin=True."""
    from src.crud.crud_role import get_roles_for_names
    roles_in_token = payload.get("realm_access", {}).get("roles", [])
    caller_roles = get_roles_for_names(db, roles_in_token)
    if not any(r.is_role_admin for r in caller_roles):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Accès réservé aux administrateurs de rôles",
        )
    return payload


# -------------------------------------------------------------------
# Dependency : codir, présidence, admin (lifecycle revoke/restore)
# -------------------------------------------------------------------
async def require_lifecycle_manager(
    payload: dict = Depends(validate_jwt),
) -> dict:
    """Codir, Présidence, Admin sys can revoke/restore accounts (hardcoded per CDC)."""
    roles = payload.get("realm_access", {}).get("roles", [])
    if not {"codir", "presidence", "admin"}.intersection(roles):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Accès réservé au Comité de direction, Présidence ou Administrateur système",
        )
    return payload


# -------------------------------------------------------------------
# Dependency : présidence et admin (lifecycle hard-delete)
# -------------------------------------------------------------------
async def require_lifecycle_admin(
    payload: dict = Depends(validate_jwt),
) -> dict:
    """Only Présidence and Admin sys can hard-delete accounts (hardcoded per CDC)."""
    roles = payload.get("realm_access", {}).get("roles", [])
    if not {"presidence", "admin"}.intersection(roles):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Accès réservé à la Présidence ou à l'Administrateur système",
        )
    return payload
