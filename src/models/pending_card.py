from sqlalchemy import Column, Integer, String, DateTime, func
from src.database.base import Base


class PendingCard(Base):
    __tablename__ = "pending_cards"

    id = Column(Integer, primary_key=True, index=True)
    card_id = Column(String, unique=True, index=True, nullable=False)
    scanned_at = Column(DateTime(timezone=True), default=func.now())
    status = Column(String, default="pending")  