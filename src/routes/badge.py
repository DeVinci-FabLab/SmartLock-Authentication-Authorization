from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError

from src.core.keycloak import require_nfc_scanner, require_admin
from src.database.session import get_db
from src.models.pending_card import PendingCard
from src.schemas.pending_card import ScanCardRequest, ScanCardResponse, PendingCardResponse
from src.utils.logger import logger

router = APIRouter(prefix="/badge", tags=["Badge"])


# -------------------------------------------------------------------
# POST /badge/scan — réservé au service account nfc-scanner
# -------------------------------------------------------------------
@router.post(
    "/scan",
    response_model=ScanCardResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Enregistrer un scan de carte NFC",
)
async def scan_card(
    body: ScanCardRequest,
    db: Session = Depends(get_db),
    _: dict = Depends(require_nfc_scanner),
):
    """
    Reçoit un card_id scanné par le module NFC et le stocke en DB.
    Protégé par le service account nfc-scanner (client_credentials).
    """
    logger.info(f"Scan reçu : card_id={body.card_id}")

    try:
        # Vérifier si la carte existe déjà
        existing = db.query(PendingCard).filter(
            PendingCard.card_id == body.card_id
        ).first()

        if existing:
            logger.warning(f"card_id={body.card_id} déjà enregistré (status={existing.status})")
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Cette carte est déjà enregistrée (status: {existing.status})",
            )

        card = PendingCard(card_id=body.card_id)
        db.add(card)
        db.commit()
        db.refresh(card)

        logger.success(f"card_id={body.card_id} enregistré avec succès")
        return ScanCardResponse(
            success=True,
            message="Carte enregistrée, en attente d'assignation par un admin",
            card_id=body.card_id,
        )

    except HTTPException:
        raise
    except SQLAlchemyError as e:
        logger.error(f"Erreur DB lors du scan : {e}")
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erreur lors de l'enregistrement de la carte",
        )


# -------------------------------------------------------------------
# GET /badge/pending — réservé aux admins Keycloak
# -------------------------------------------------------------------
@router.get(
    "/pending",
    response_model=List[PendingCardResponse],
    summary="Lister les cartes en attente d'assignation",
)
async def get_pending_cards(
    db: Session = Depends(get_db),
    _: dict = Depends(require_admin),
):
    """
    Retourne toutes les cartes scannées avec status 'pending'.
    Protégé — réservé aux administrateurs Keycloak.
    """
    try:
        cards = db.query(PendingCard).filter(
            PendingCard.status == "pending"
        ).order_by(PendingCard.scanned_at.desc()).all()

        logger.info(f"{len(cards)} carte(s) en attente")
        return cards

    except SQLAlchemyError as e:
        logger.error(f"Erreur DB lors de la récupération des cartes : {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erreur lors de la récupération des cartes",
        )


# -------------------------------------------------------------------
# PATCH /badge/{card_id}/assign — marquer une carte comme assignée
# -------------------------------------------------------------------
@router.patch(
    "/{card_id}/assign",
    response_model=PendingCardResponse,
    summary="Marquer une carte comme assignée",
)
async def mark_card_assigned(
    card_id: str,
    db: Session = Depends(get_db),
    _: dict = Depends(require_admin),
):
    """
    Une fois l'admin a entré le card_id dans Keycloak manuellement,
    il marque la carte comme assignée pour la retirer de la liste pending.
    """
    try:
        card = db.query(PendingCard).filter(
            PendingCard.card_id == card_id
        ).first()

        if not card:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Carte introuvable",
            )

        card.status = "assigned"
        db.commit()
        db.refresh(card)

        logger.success(f"card_id={card_id} marquée comme assignée")
        return card

    except HTTPException:
        raise
    except SQLAlchemyError as e:
        logger.error(f"Erreur DB lors de l'assignation : {e}")
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erreur lors de la mise à jour",
        )