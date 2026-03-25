from pydantic import BaseModel, Field, ConfigDict
from typing import Optional
from datetime import datetime

class AccessLogBase(BaseModel):
    """Base schema for Access Logs"""
    locker_id: Optional[int] = Field(None, description="ID of the locker accessed")
    card_id: str = Field(..., description="NFC Card ID scanned")
    user_id: Optional[str] = Field(None, description="Keycloak User UUID (if known)")
    username: Optional[str] = Field(None, description="User display name")
    
    result: str = Field(..., description="'allowed' or 'denied'")
    reason: Optional[str] = Field(None, description="Reason for denial or context")
    
    can_open: Optional[bool] = Field(None, description="Snapshot: was user allowed to open?")
    can_view: Optional[bool] = Field(None, description="Snapshot: was user allowed to view?")

class AccessLogCreate(AccessLogBase):
    """Schema for creating a new access log"""
    pass

class AccessLogResponse(AccessLogBase):
    """Schema for access log response"""
    id: int
    timestamp: datetime
    
    model_config = ConfigDict(from_attributes=True)