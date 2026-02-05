from pydantic import BaseModel, Field, ConfigDict
from datetime import datetime
from typing import Optional, List, TYPE_CHECKING

if TYPE_CHECKING:
    from .items import ItemResponse

class CategoryBase(BaseModel):
    """Base schema for Category with common fields"""
    name: str = Field(..., min_length=1, max_length=100, description="Category name")


class CategoryCreate(CategoryBase):
    """Schema for creating a new category"""
    pass


class CategoryUpdate(BaseModel):
    """Schema for updating a category (all fields optional)"""
    name: Optional[str] = Field(None, min_length=1, max_length=100)


class CategoryResponse(CategoryBase):
    """Schema for category response"""
    id: int
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    
    model_config = ConfigDict(from_attributes=True)


class CategoryWithItems(CategoryResponse):
    """Category with its items included"""
    items: List["ItemResponse"] = []