from sqlalchemy import Boolean, Column, DateTime, Integer, String, func
from sqlalchemy.types import JSON
from src.database.base import Base


class Role(Base):
    __tablename__ = "roles"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), unique=True, nullable=False, index=True)
    label = Column(String(255), nullable=False)
    tier = Column(Integer, nullable=False)
    is_system = Column(Boolean, default=False, nullable=False)
    is_manager = Column(Boolean, default=False, nullable=False)
    is_role_admin = Column(Boolean, default=False, nullable=False)
    capacities = Column(JSON, default=list, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
