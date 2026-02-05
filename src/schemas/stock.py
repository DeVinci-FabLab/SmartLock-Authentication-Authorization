from pydantic import BaseModel, Field, ConfigDict
from datetime import datetime
from typing import Optional, TYPE_CHECKING 

if TYPE_CHECKING:
    from .items import ItemResponse
    from .lockers import LockerResponse

class StockBase(BaseModel):
    quantity: int = Field(default=0, ge=0, description="Quantity in stock")
    item_id: int = Field(..., gt=0, description="Item ID")
    locker_id: int = Field(..., gt=0, description="Locker ID")
    unit_measure: str = Field(default="units", max_length=50, description="Unit of measure")

class StockCreate(StockBase):
    pass

class StockUpdate(BaseModel):
    quantity: Optional[int] = Field(None, ge=0)
    item_id: Optional[int] = Field(None, gt=0)
    locker_id: Optional[int] = Field(None, gt=0)
    unit_measure: Optional[str] = Field(None, max_length=50)

class StockResponse(StockBase):
    id: int
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    
    model_config = ConfigDict(from_attributes=True)

class StockWithDetails(StockResponse):
    # 3. Use strings "ItemResponse" instead of the actual class object
    item: Optional["ItemResponse"] = None
    locker: Optional["LockerResponse"] = None