from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import relationship

from src.database.base import Base


class Locker_Permission(Base):
    __tablename__ = "locker_permissions"

    id = Column(Integer, primary_key=True, index=True)
    locker_id = Column(
        Integer, ForeignKey("lockers.id", ondelete="CASCADE"), nullable=False
    )

    # --- NOUVEAU : Cible hybride (Rôle ou Utilisateur) ---
    subject_type = Column(String, default="role", nullable=False)  # "role" ou "user"
    role_name = Column(String, index=True, nullable=True)  # Nom du rôle Keycloak
    user_id = Column(
        String, index=True, nullable=True
    )  # UUID de l'utilisateur Keycloak

    # --- Permissions ---
    can_view = Column(Boolean, default=True)
    can_open = Column(Boolean, default=False)
    can_edit = Column(Boolean, default=False)
    can_take = Column(Boolean, default=False)
    can_manage = Column(Boolean, default=False)

    # --- Métadonnées ---
    valid_until = Column(String, nullable=True)  # Format ISO ou null (sans expiration)
    created_at = Column(DateTime(timezone=True), default=func.now())

    locker = relationship("Lockers", back_populates="permissions")

    __table_args__ = (
        # Unicité combinée pour éviter les doublons sur un même casier
        UniqueConstraint(
            "locker_id", "role_name", "user_id", name="unique_permission_target"
        ),
    )
