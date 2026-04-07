from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class PendingCardResponse(BaseModel):
    id: int
    card_id: str
    scanned_at: Optional[datetime] = None
    status: str

    model_config = ConfigDict(from_attributes=True)


class ScanCardRequest(BaseModel):
    card_id: str = Field(
        ..., min_length=1, max_length=64, description="ID de la carte NFC"
    )


class ScanCardResponse(BaseModel):
    success: bool
    message: str
    card_id: str
