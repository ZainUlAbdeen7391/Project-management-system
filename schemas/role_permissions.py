from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime


class PermissionBase(BaseModel):
    module_id: str
    role_id: str
    permission_name: str = Field(..., max_length=100)
    permission_slug: str = Field(..., max_length=100)
    resource: str = Field(..., max_length=50)
    action: str = Field(..., max_length=50)
    description: Optional[str] = Field(None, max_length=255)
    status: int = Field(default=1)


class PermissionCreate(PermissionBase):
    pass


class PermissionUpdate(BaseModel):
    module_id: Optional[str] = None
    role_id: Optional[str] = None
    permission_name: Optional[str] = Field(None, max_length=100)
    permission_slug: Optional[str] = Field(None, max_length=100)
    resource: Optional[str] = Field(None, max_length=50)
    action: Optional[str] = Field(None, max_length=50)
    description: Optional[str] = Field(None, max_length=255)
    status: Optional[int] = None


class PermissionOut(PermissionBase):
    permission_id: str
    created_on: datetime
    updated_on: datetime
    deleted_on: Optional[datetime] = None
    module_name: Optional[str] = None
    module_slug: Optional[str] = None
    role_name: Optional[str] = None
    role_slug: Optional[str] = None


class UserRoleSummary(BaseModel):
    role_id: str
    role_name: str
    role_slug: str


class UserPermissionSummary(BaseModel):
    module_slug: str
    resource: str
    action: str
    permission_slug: str
    permission_name: str


class LoginSuccessResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user_id: str
    full_name: str
    roles: List[UserRoleSummary]
    permissions: List[UserPermissionSummary]