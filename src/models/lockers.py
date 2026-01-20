from sqlalchemy import Column, Date, Integer, String, Boolean
from src.database.base import Base
from sqlalchemy.orm import relationship

class Lockers(Base):
    __tablename__ = "lockers"

    id = Column(Integer, primary_key=True, index=True)
    locker_type = Column(String, index=True)
    is_active = Column(Boolean, default=True)  
    created_at = Column(Date)
    updated_at = Column(Date)
    
    stock = relationship("Stock", back_populates="locker")