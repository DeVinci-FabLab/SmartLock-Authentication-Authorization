from pydantic import BaseModel, Field, ConfigDict
from datetime import datetime
from typing import Optional, List
from .stock import StockResponse
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .stock import StockResponse

class LockerBase(BaseModel):
    """Base schema for Locker with common fields"""
    locker_type: str = Field(..., min_length=1, max_length=50, description="Type of locker")
    is_active: bool = Field(default=True, description="Locker active status")


class LockerCreate(LockerBase):
    """Schema for creating a new locker"""
    pass


class LockerUpdate(BaseModel):
    """Schema for updating a locker (all fields optional)"""
    locker_type: Optional[str] = Field(None, min_length=1, max_length=50)
    is_active: Optional[bool] = None


class LockerResponse(LockerBase):
    """Schema for locker response"""
    id: int
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    
    model_config = ConfigDict(from_attributes=True)


class LockerWithStock(LockerResponse):
    """Locker with its stock information"""
    stock: List["StockResponse"] = []
