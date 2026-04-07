from sqlalchemy import Column, DateTime, Integer, String, func
from sqlalchemy.orm import relationship

from src.database.base import Base


class Categories(Base):
    __tablename__ = "categories"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True, nullable=False)
    created_at = Column(DateTime(timezone=True), default=func.now())
    updated_at = Column(
        DateTime(timezone=True), default=func.now(), onupdate=func.now()
    )

    items = relationship(
        "Items", back_populates="category", cascade="all, delete-orphan"
    )
