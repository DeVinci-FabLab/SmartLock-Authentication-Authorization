from pydantic import BaseModel, Field, ConfigDict
from datetime import date
from typing import Optional
from .items import ItemResponse
from .lockers import LockerResponse

class StockBase(BaseModel):
    """Base schema for Stock with common fields"""
    quantity: int = Field(default=0, ge=0, description="Quantity in stock")
    item_id: int = Field(..., gt=0, description="Item ID")
    locker_id: int = Field(..., gt=0, description="Locker ID")
    unit_measure: str = Field(default="units", max_length=50, description="Unit of measure")


class StockCreate(StockBase):
    """Schema for creating a new stock entry"""
    pass


class StockUpdate(BaseModel):
    """Schema for updating stock (all fields optional)"""
    quantity: Optional[int] = Field(None, ge=0)
    item_id: Optional[int] = Field(None, gt=0)
    locker_id: Optional[int] = Field(None, gt=0)
    unit_measure: Optional[str] = Field(None, max_length=50)


class StockResponse(StockBase):
    """Schema for stock response"""
    id: int
    created_at: Optional[date] = None
    
    model_config = ConfigDict(from_attributes=True)


class StockWithDetails(StockResponse):
    """Stock with item and locker information"""
    item: Optional[ItemResponse] = None
    locker: Optional[LockerResponse] = None