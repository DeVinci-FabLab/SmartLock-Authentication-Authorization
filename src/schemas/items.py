from pydantic import BaseModel, Field, ConfigDict
from datetime import datetime
from typing import Optional, List
from .categories import CategoryResponse
from .stock import StockResponse
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .categories import CategoryResponse
    from .stock import StockResponse

class ItemBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=255, description="Item name")
    reference: str = Field(..., min_length=1, max_length=50, description="Unique reference code")
    description: Optional[str] = Field(None, description="Item description")
    category_id: int = Field(..., gt=0, description="Category ID")


class ItemCreate(ItemBase):
    """Schema for creating a new item"""
    pass


class ItemUpdate(BaseModel):
    """Schema for updating an item (all fields optional)"""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    reference: Optional[str] = Field(None, min_length=1, max_length=50)
    description: Optional[str] = None
    category_id: Optional[int] = Field(None, gt=0)

class ItemResponse(ItemBase):
    id: int
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    
    model_config = ConfigDict(from_attributes=True)

class ItemWithDetails(ItemResponse):
    """Item with category and stock information"""

    category: Optional["CategoryResponse"] = None
    stock: List["StockResponse"] = []