from datetime import datetime
from sqlalchemy import Column, Integer, String, ForeignKey, Boolean, DateTime
from src.database.base import Base
from sqlalchemy.orm import relationship


class AccessLog(Base):
    __tablename__ = "access_logs"

    id = Column(Integer, primary_key=True, index=True)
    locker_id = Column(
        Integer, ForeignKey("lockers.id", ondelete="CASCADE"), nullable=False
    )
    card_id = Column(String, nullable=False, index=True)

    user_id = Column(
        String, nullable=True, index=True
    )  # UUID Keycloak (null si badge inconnu)
    username = Column(String, nullable=True)  # Nom d'affichage pour lisibilité

    result = Column(String, nullable=False)  # "allowed" ou "denied"
    reason = Column(
        String, nullable=True
    )  # "no_permission", "card_not_registered", "expired", etc.

    # Snapshot des permissions au moment du scan
    can_open = Column(Boolean, nullable=True)
    can_view = Column(Boolean, nullable=True)

    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relation (optionnelle, suppose que le modèle Lockers existe)
    locker = relationship("Lockers", back_populates="access_logs")
