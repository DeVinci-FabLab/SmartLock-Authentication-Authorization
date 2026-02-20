from sqlalchemy import Column, DateTime, Integer, String, Boolean, func
from src.database.base import Base
from sqlalchemy.orm import relationship

class Lockers(Base):
    __tablename__ = "lockers"

    id = Column(Integer, primary_key=True, index=True)
    locker_type = Column(String, index=True)
    is_active = Column(Boolean, default=True)  
    created_at = Column(DateTime(timezone=True), default=func.now())
    updated_at = Column(DateTime(timezone=True), default=func.now(), onupdate=func.now())
    
    stock = relationship("Stock", back_populates="locker")
    permissions = relationship("Locker_Permission", back_populates="locker")