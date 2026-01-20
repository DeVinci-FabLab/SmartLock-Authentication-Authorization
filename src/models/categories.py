from sqlalchemy import Column, Integer, String, Date
from sqlalchemy.orm import relationship
from src.database.base import Base

class Categories(Base):
    __tablename__ = "categories"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True)
    created_at = Column(Date)
    updated_at = Column(Date)

    items = relationship("Items", back_populates="category")