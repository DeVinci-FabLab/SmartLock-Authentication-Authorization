from sqlalchemy import Column, DateTime, Integer, String, ForeignKey, UniqueConstraint, func
from src.database.base import Base
from sqlalchemy.orm import relationship

class Stock(Base):
    __tablename__ = "stock"

    id = Column(Integer, primary_key=True, index=True)
    quantity = Column(Integer, default=0)
    item_id = Column(Integer, ForeignKey("items.id"), nullable=False)
    locker_id = Column(Integer, ForeignKey("lockers.id"), nullable=False)
    unit_measure = Column(String, default="units")
    created_at = Column(DateTime(timezone=True), default=func.now())
    updated_at = Column(DateTime(timezone=True), default=func.now(), onupdate=func.now())
    
    item = relationship("Items", back_populates="stock")
    locker = relationship("Lockers", back_populates="stock")
