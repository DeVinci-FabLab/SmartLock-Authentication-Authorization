from typing import Optional
from pydantic import BaseModel, ConfigDict, field_validator

PERMISSION_LEVELS = ("can_view", "can_open", "can_edit")


class LockerPermissionBase(BaseModel):
    role_name: str
    permission_level: str
    valid_until: Optional[str] = None
    locker_id: int

    @field_validator("permission_level")
    @classmethod
    def level_valid(cls, v: str) -> str:
        if v not in PERMISSION_LEVELS:
            raise ValueError(f"permission_level must be one of {PERMISSION_LEVELS}")
        return v


class LockerPermissionCreate(LockerPermissionBase):
    pass


class LockerPermissionUpdate(BaseModel):
    permission_level: Optional[str] = None
    valid_until: Optional[str] = None

    @field_validator("permission_level")
    @classmethod
    def level_valid(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and v not in PERMISSION_LEVELS:
            raise ValueError(f"permission_level must be one of {PERMISSION_LEVELS}")
        return v


class LockerPermissionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    locker_id: int
    role_name: str
    permission_level: str
    valid_until: Optional[str] = None
    created_at: Optional[str] = None
