from sqlalchemy import Column, Integer, String, ForeignKey, Boolean, UniqueConstraint
from src.database.base import Base
from sqlalchemy.orm import relationship

class Locker_Permission(Base):
    __tablename__ = "locker_permissions"

    id = Column(Integer, primary_key=True, index=True)
    role_name = Column(String, index=True)
    can_view = Column(Boolean, default=True)
    can_open = Column(Boolean, default=False)
    can_edit = Column(Boolean, default=False)
    can_take = Column(Boolean, default=False)
    can_manage = Column(Boolean, default=False)
    valid_until = Column(String, nullable=True)  # ISO date string or null for no expiration
    created_at = Column(String)  # ISO date string
    locker_id = Column(Integer, ForeignKey("lockers.id"), nullable=False)
    
    locker = relationship("Lockers", back_populates="permissions")
    
    __table_args__ = (
        UniqueConstraint('role_name', 'locker_id', name='unique_role_locker'),
    )