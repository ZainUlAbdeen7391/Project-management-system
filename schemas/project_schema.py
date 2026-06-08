from pydantic import BaseModel, Field, field_validator, model_validator
from datetime import date, datetime
from decimal import Decimal
from typing import Optional, List
from enum import Enum


class ProjectType(str, Enum):
    internal = "Internal"
    external = "External"

class ProjectStatus(str, Enum):
    planning = "planning"
    active = "active"
    on_hold = "on_hold"
    completed = "completed"
    cancelled = "cancelled"

class ProjectCreateRequest(BaseModel):
    project_name: str = Field(..., min_length=1, max_length=150)
    description: Optional[str] = None
    project_type: ProjectType = ProjectType.external
    client_id: Optional[int] = None
    estimated_cost: Optional[Decimal] = Field(default=None,ge=Decimal("0.00"),decimal_places=2,max_digits=10,)
    due_date: Optional[date] = None
  
    @field_validator("due_date")
    @classmethod
    def validate_due_date(cls, v):
        if v is not None and v < date.today():
            raise ValueError("due_date cannot be in the past")
        return v

    @model_validator(mode="after")
    def validate_client(self):
        if self.project_type == ProjectType.external:
            if self.client_id is None:
                raise ValueError("client_id is required for External projects")
        if self.project_type == ProjectType.internal:
            self.client_id = None
        return self


class ProjectResponse(BaseModel):
    success: bool
    message: str
    project_id: int
    project_name: str
    description: Optional[str] = None
    project_type: str
    client_id: Optional[int] = None
    estimated_cost: Optional[Decimal] = None
    due_date: Optional[date] = None
    start_date: Optional[datetime] = None
    end_date: Optional[date] = None
    status: str
    created_by: Optional[int] = None
    created_on: Optional[datetime] = None
    updated_on: Optional[datetime] = None


class ProjectListItem(BaseModel):
    project_id: int
    project_name: str
    description: Optional[str] = None
    project_type: str
    client_id: Optional[int] = None
    client_name: Optional[str] = None
    estimated_cost: Optional[Decimal] = None
    due_date: Optional[date] = None
    start_date: Optional[datetime] = None
    end_date: Optional[date] = None
    status: str
    created_by: Optional[int] = None
    created_by_name: Optional[str] = None
    created_on: Optional[datetime] = None
    updated_on: Optional[datetime] = None


class ProjectListResponse(BaseModel):
    success: bool
    message: str
    count: int
    data: list[ProjectListItem]


class ProjectUpdateRequest(BaseModel):
    project_name: Optional[str] = Field(None, min_length=1, max_length=150)
    description: Optional[str] = None
    project_type: Optional[ProjectType] = None
    client_id: Optional[int] = None
    estimated_cost: Optional[Decimal] = Field(None, ge=Decimal("0.00"), decimal_places=2, max_digits=10)
    due_date: Optional[date] = None
    end_date: Optional[date] = None
    status: Optional[ProjectStatus] = None

    @field_validator("end_date", "due_date", mode="before")
    @classmethod
    def empty_string_to_none(cls, v):
        if isinstance(v, str) and v.strip().lower() in ("null", "none", ""):
            return None
        return v

    @field_validator("due_date")
    @classmethod
    def validate_due_date(cls, v: Optional[date]) -> Optional[date]:
        if v is not None and v < date.today():
            raise ValueError("due_date cannot be in the past")
        return v


class ProjectMemberCreateRequest(BaseModel):
    members: List[int] = Field(..., min_length=1)
    project_managers: List[int] = Field(..., min_length=1)

    @field_validator("members", "project_managers")
    @classmethod
    def no_duplicates(cls, v: List[int]) -> List[int]:
        if len(v) != len(set(v)):
            raise ValueError("Duplicate IDs are not allowed")
        return v


class ProjectMemberResponse(BaseModel):
    success: bool
    message: str
    project_id: int
    assigned_count: int
    members: List[int]
    project_managers: List[int]
    
    
    
    