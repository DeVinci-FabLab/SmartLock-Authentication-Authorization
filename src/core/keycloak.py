"""
Keycloak integration
====================
- validate_jwt()        : vérifie le Bearer JWT (admins ET service accounts)
- require_role()        : vérifie qu'un rôle Keycloak est présent dans le token
- is_nfc_scanner()      : vérifie que le token appartient au service account nfc-scanner
"""

import httpx
from jose import jwt, JWTError
from fastapi import HTTPException, Security, status, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from src.core.config import settings
from src.utils.logger import logger

bearer_scheme = HTTPBearer()

NFC_SCANNER_CLIENT_ID = "nfc-scanner"


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
# Dependency : réservé aux admins Keycloak
# -------------------------------------------------------------------
async def require_admin(
    payload: dict = Depends(validate_jwt),
) -> dict:
    """
    Vérifie que le token contient le rôle 'admin' dans realm_access.roles.
    """
    roles = payload.get("realm_access", {}).get("roles", [])
    if "admin" not in roles:
        logger.warning(f"Accès refusé — roles={roles}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Accès réservé aux administrateurs",
        )
    return payload