from pydantic import BaseModel, Field, ConfigDict, model_validator
from typing import Optional
from .lockers import LockerResponse


class LockerPermissionBase(BaseModel):
    """Base schema for Locker Permission with common fields"""

    subject_type: str = Field(
        default="role", description="Type of target: 'role' or 'user'"
    )
    role_name: Optional[str] = Field(
        None,
        min_length=1,
        max_length=100,
        description="Role name (if subject_type is 'role')",
    )
    user_id: Optional[str] = Field(
        None, description="Keycloak User UUID (if subject_type is 'user')"
    )

    can_view: bool = Field(default=True, description="Can view locker")
    can_open: bool = Field(default=False, description="Can open locker")
    can_edit: bool = Field(default=False, description="Can edit locker")
    can_take: bool = Field(default=False, description="Can take items")
    can_manage: bool = Field(default=False, description="Can manage locker")
    valid_until: Optional[str] = Field(None, description="Expiration date (ISO format)")
    locker_id: int = Field(..., gt=0, description="Locker ID")

    @model_validator(mode="after")
    def check_subject_target(self) -> "LockerPermissionBase":
        if self.subject_type == "role" and not self.role_name:
            raise ValueError("role_name is required when subject_type is 'role'")
        if self.subject_type == "user" and not self.user_id:
            raise ValueError("user_id is required when subject_type is 'user'")
        return self


class LockerPermissionCreate(LockerPermissionBase):
    """Schema for creating a new locker permission"""

    pass


class LockerPermissionUpdate(BaseModel):
    """Schema for updating locker permission (all fields optional)"""

    subject_type: Optional[str] = Field(
        None, description="Type of target: 'role' or 'user'"
    )
    role_name: Optional[str] = Field(None, min_length=1, max_length=100)
    user_id: Optional[str] = Field(None)
    can_view: Optional[bool] = None
    can_open: Optional[bool] = None
    can_edit: Optional[bool] = None
    can_take: Optional[bool] = None
    can_manage: Optional[bool] = None
    valid_until: Optional[str] = None
    locker_id: Optional[int] = Field(None, gt=0)


class LockerPermissionResponse(LockerPermissionBase):
    """Schema for locker permission response"""

    id: int
    created_at: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class LockerPermissionWithDetails(LockerPermissionResponse):
    """Locker permission with locker information"""

    locker: Optional[LockerResponse] = None
