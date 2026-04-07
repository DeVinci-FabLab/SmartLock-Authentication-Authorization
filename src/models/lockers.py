from sqlalchemy import Boolean, Column, DateTime, Integer, String, func
from sqlalchemy.orm import relationship

from src.database.base import Base


class Lockers(Base):
    __tablename__ = "lockers"

    id = Column(Integer, primary_key=True, index=True)
    locker_type = Column(String, index=True, nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), default=func.now())
    updated_at = Column(
        DateTime(timezone=True), default=func.now(), onupdate=func.now()
    )

    permissions = relationship(
        "Locker_Permission", back_populates="locker", cascade="all, delete-orphan"
    )
    stock = relationship("Stock", back_populates="locker", cascade="all, delete-orphan")
    access_logs = relationship(
        "AccessLog", back_populates="locker", cascade="all, delete-orphan"
    )
