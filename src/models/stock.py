from sqlalchemy import Column, Date, Integer, String, ForeignKey, UniqueConstraint
from src.database.base import Base
from sqlalchemy.orm import relationship

class Stock(Base):
    __tablename__ = "stock"

    id = Column(Integer, primary_key=True, index=True)
    quantity = Column(Integer, default=0)
    item_id = Column(Integer, ForeignKey("items.id"), nullable=False)
    locker_id = Column(Integer, ForeignKey("lockers.id"), nullable=False)
    unit_measure = Column(String, default="units")
    created_at = Column(Date)

    item = relationship("Items", back_populates="stock")
    locker = relationship("Lockers", back_populates="stock")
    
    __table_args__ = (
        UniqueConstraint('item_id', 'locker_id', name='unique_item_locker'),
    )