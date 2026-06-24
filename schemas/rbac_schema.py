from pydantic import BaseModel, Field, RootModel
from typing import Optional, List, Dict, Any
from datetime import datetime

class RoleBase(BaseModel):
    role_name: str = Field(..., max_length=50)
    role_slug: str = Field(..., max_length=50)
    description: Optional[str] = Field(None, max_length=255)

class RoleCreate(RoleBase):
    pass


class RoleUpdate(BaseModel):
    role_name: str = Field(..., max_length=50)
    role_slug: str = Field(..., max_length=50)
    description: Optional[str] = Field(None, max_length=255)


class RoleOut(BaseModel):
    role_id: str
    role_name: str
    role_slug: str
    description: Optional[str]
    status: int
    created_by: str
    updated_by: str
    created_on: datetime
    updated_on: datetime



class ModuleOut(BaseModel):
    module_id: str
    module_name: str
    module_slug: str
    description: Optional[str]
    status: int
    created_by: str
    updated_by: str
    created_on: datetime
    updated_on: datetime



class UserRoleCreate(BaseModel):
    user_id: str
    role_id: str
    status: str = Field(default="active")


class UserRoleUpdate(BaseModel):
    status: Optional[str] = None


class UserRoleOut(BaseModel):
    ur_id: str
    user_id: str
    role_id: str
    status: int
    created_on: datetime
    updated_on: datetime
    role_name: Optional[str] = None
    role_slug: Optional[str] = None



class PermissionMatrixItem(BaseModel):
    permission_id: str
    permission_name: str
    resource: str
    action: str
    permission_slug: str


class PermissionMatrixOut(RootModel[Dict[str, Dict[str, List[PermissionMatrixItem]]]]):
    pass

class ApiResponse(BaseModel):
    success: bool
    message: str
    data: Any