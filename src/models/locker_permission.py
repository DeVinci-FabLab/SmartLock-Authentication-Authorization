from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, UniqueConstraint, func
from sqlalchemy.orm import relationship
from src.database.base import Base


PERMISSION_LEVELS = ("can_view", "can_open", "can_edit")
PERMISSION_ORDER = {level: idx for idx, level in enumerate(PERMISSION_LEVELS)}


class Locker_Permission(Base):
    __tablename__ = "locker_permissions"

    id = Column(Integer, primary_key=True, index=True)
    locker_id = Column(Integer, ForeignKey("lockers.id", ondelete="CASCADE"), nullable=False)
    role_name = Column(String(100), index=True, nullable=False)
    permission_level = Column(String(20), nullable=False, default="can_view")
    valid_until = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    locker = relationship("Lockers", back_populates="permissions")

    __table_args__ = (
        UniqueConstraint("locker_id", "role_name", name="unique_permission_role_locker"),
    )
