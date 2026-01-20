from sqlalchemy import Column, Integer, String, ForeignKey, Date
from sqlalchemy.orm import relationship
from src.database.base import Base

class Items(Base):
    __tablename__ = "items"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    reference = Column(String, unique=True, index=True)
    description = Column(String)
    category_id = Column(Integer, ForeignKey("categories.id"), nullable=False)
    created_at = Column(Date)
    updated_at = Column(Date)

    stock = relationship("Stock", back_populates="item")
    category = relationship("Categories", back_populates="items")