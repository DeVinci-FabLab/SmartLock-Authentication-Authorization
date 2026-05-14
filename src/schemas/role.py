from typing import Optional
from pydantic import BaseModel, ConfigDict, field_validator


VALID_CAPACITIES = {
    "create_lockers", "configure_system", "audit_log_full",
    "purchase_orders", "manage_suppliers", "cascade_delete_role",
    "validate_catalog", "manage_stock_thresholds",
}


class RoleBase(BaseModel):
    label: str
    tier: int
    is_manager: bool = False
    is_role_admin: bool = False
    capacities: list[str] = []

    @field_validator("tier")
    @classmethod
    def tier_in_range(cls, v: int) -> int:
        if not (0 <= v <= 4):
            raise ValueError("tier must be between 0 and 4 for custom roles (T5 is reserved)")
        return v

    @field_validator("capacities")
    @classmethod
    def capacities_valid(cls, v: list[str]) -> list[str]:
        invalid = set(v) - VALID_CAPACITIES
        if invalid:
            raise ValueError(f"Unknown capacities: {invalid}")
        return v


class RoleCreate(RoleBase):
    name: str


class RoleUpdate(BaseModel):
    label: Optional[str] = None
    is_manager: Optional[bool] = None
    is_role_admin: Optional[bool] = None
    capacities: Optional[list[str]] = None

    @field_validator("capacities")
    @classmethod
    def capacities_valid(cls, v: Optional[list[str]]) -> Optional[list[str]]:
        if v is None:
            return v
        invalid = set(v) - VALID_CAPACITIES
        if invalid:
            raise ValueError(f"Unknown capacities: {invalid}")
        return v


class RoleResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    label: str
    tier: int
    is_system: bool
    is_manager: bool
    is_role_admin: bool
    capacities: list[str]
