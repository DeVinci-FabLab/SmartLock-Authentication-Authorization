from fastapi import APIRouter, Depends, status, Query
from pydantic import BaseModel, EmailStr
from typing import List, Dict, Any, Optional

from src.core.keycloak import require_admin
from src.core.keycloak_admin import (
    list_users,
    set_user_card_id,
    assign_user_to_group,
    remove_user_from_group,
    list_groups,
)

# Toutes ces routes sont strictement réservées aux administrateurs
router = APIRouter(
    tags=["User Management (Keycloak)"], dependencies=[Depends(require_admin)]
)


class CardUpdateRequest(BaseModel):
    card_id: str


# --- Routes Utilisateurs ---


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


@router.patch("/users/{user_id}/card")
async def update_user_card(user_id: str, card_data: CardUpdateRequest):
    """Associe ou met à jour le badge NFC (card_id) d'un utilisateur."""
    await set_user_card_id(user_id=user_id, card_id=card_data.card_id)
    return {"message": f"Badge {card_data.card_id} associé à l'utilisateur {user_id}"}


@router.put("/users/{user_id}/groups/{group_id}")
async def add_user_to_group(user_id: str, group_id: str):
    """Ajoute un utilisateur à un groupe Keycloak."""
    await assign_user_to_group(user_id=user_id, group_id=group_id)
    return {"message": "Utilisateur ajouté au groupe"}


@router.delete(
    "/users/{user_id}/groups/{group_id}", status_code=status.HTTP_204_NO_CONTENT
)
async def remove_user_from_group_endpoint(user_id: str, group_id: str):
    """Retire un utilisateur d'un groupe Keycloak."""
    await remove_user_from_group(user_id=user_id, group_id=group_id)


# --- Routes Groupes ---


@router.get("/groups")
async def get_all_groups():
    """Liste tous les groupes disponibles dans Keycloak."""
    return await list_groups()
