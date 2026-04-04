from typing import Optional

from fastapi import APIRouter, Depends, Query

from src.core.keycloak import require_admin
from src.core.keycloak_admin import (
    list_groups,
    list_users,
)

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


# --- Routes Groupes (lecture seule) ---


@router.get("/groups")
async def get_all_groups():
    """Liste tous les groupes disponibles dans Keycloak."""
    return await list_groups()
