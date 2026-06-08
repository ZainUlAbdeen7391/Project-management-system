
from pydantic import BaseModel, Field, RootModel

from typing import Optional, List, Dict, Any
from datetime import datetime

#Role
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
    role_id: int
    role_name: str
    role_slug: str
    description: Optional[str] 
    status: int
    created_by: int
    updated_by: int 
    created_on: datetime
    updated_on: datetime 
    deleted_on: Optional[datetime]=None
    
    
#Module

class ModuleOut(BaseModel):
    module_id: int 
    module_name: str 
    module_slug: str 
    description: Optional[str]
    status: int 
    created_by: int
    updated_by: int 
    created_on: datetime
    updated_on: datetime 
    deleted_on: Optional[datetime] =None
    
#Permission

class PermissionBase(BaseModel):
    module_id: int 
    role_id: int
    permission_name: str = Field(..., max_length=100)
    permission_slug: str = Field(..., max_length=100)
    resource: str = Field(..., max_length=50)
    action: str = Field(..., max_length=50)
    description: Optional[str] = Field(None, max_length=255) 
    status: int = Field(default=1)
    
class PermissionCreate(PermissionBase):
    pass

class PermissionUpdate(BaseModel):
    permission_name: str = Field(..., max_length=100)
    permission_slug: str = Field(..., max_length=100)
    resource: str = Field(...,max_length=50)
    action: str = Field(..., max_length=50)
    description: Optional[str] = Field(None, max_length=255)
    status: int = Field(default=1)
    
class PermissionOut(PermissionBase):
    permission_id: int
    created_on: datetime
    updated_on: datetime
    deleted_on: Optional[datetime] = None
    module_name: Optional[str] = None
    module_slug: Optional[str] = None
    role_name: Optional[str] = None
    role_slug: Optional[str] = None
    
    
# User Role Assignment


class UserRoleCreate(BaseModel):
    user_id: int
    role_id: int
    status: str = Field(default="active")

class UserRoleUpdate(BaseModel):
    status: Optional[str] = None

class UserRoleOut(BaseModel):
    ur_id: int
    user_id: int
    role_id: int
    status: int
    created_on: datetime
    updated_on: datetime
    deleted_on: Optional[datetime] = None
    role_name: Optional[str] = None
    role_slug: Optional[str] = None


# Permission Response
class PermissionMatrixItem(BaseModel):
    permission_id: int
    permission_name: str
    resource: str
    action: str
    permission_slug: str

class PermissionMatrixOut(
    RootModel[
        Dict[str, Dict[str, List[PermissionMatrixItem]]]
    ]
):
    pass

class ApiResponse(BaseModel):
    success: bool
    message: str
    data: Any
