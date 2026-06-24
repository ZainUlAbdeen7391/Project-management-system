from pydantic import BaseModel, Field, field_validator
from datetime import date, datetime
from typing import Optional
from enum import Enum


class TaskStatus(str, Enum):
    todo = "todo"
    in_progress = "in_progress"
    completed = "completed"


class TaskPriority(str, Enum):
    low = "low"
    medium = "medium"
    high = "high"
    urgent = "urgent"


class TaskCreateRequest(BaseModel):
    project_id: str
    title: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    status: TaskStatus = TaskStatus.todo
    priority: TaskPriority = TaskPriority.medium
    is_responsible: str            
    assignees: list[str] = Field(..., min_length=1)
    due_date: Optional[date] = None
    parent_id: Optional[str] = None

    @field_validator("due_date")
    @classmethod
    def validate_due_date(cls, v: Optional[date]) -> Optional[date]:
        if v is not None and v < date.today():
            raise ValueError("due_date cannot be in the past")
        return v


class TaskUpdateRequest(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    status: Optional[TaskStatus] = None
    priority: Optional[TaskPriority] = None
    is_responsible: Optional[str] = None
    assignees: Optional[list[str]] = Field(default=None, min_length=1)
    due_date: Optional[date] = None
    parent_id: Optional[str] = None

    @field_validator("due_date", mode="before")
    @classmethod
    def coerce_null_string(cls, v):
        if isinstance(v, str) and v.strip().lower() in ("null", "none", ""):
            return None
        return v

    @field_validator("due_date")
    @classmethod
    def validate_due_date(cls, v: Optional[date]) -> Optional[date]:
        if v is not None and v < date.today():
            raise ValueError("due_date cannot be in the past")
        return v


class TaskAssigneeItem(BaseModel):
    user_id: str
    full_name: Optional[str] = None


class TaskResponse(BaseModel):
    success: bool
    message: str
    task_id: str
    project_id: str
    title: str
    description: Optional[str] = None
    status: str
    priority: str
    is_responsible: str
    assignees: list[TaskAssigneeItem] = []
    due_date: Optional[date] = None
    completed_at: Optional[datetime] = None
    completed_by: Optional[str] = None
    parent_id: Optional[str] = None
    created_by: Optional[str] = None
    created_on: Optional[datetime] = None
    updated_on: Optional[datetime] = None


class TaskListItem(BaseModel):
    task_id: str
    project_id: str
    project_name: Optional[str] = None
    title: str
    description: Optional[str] = None
    status: str
    priority: str
    is_responsible: str
    responsible_name: Optional[str] = None
    assignees: list[TaskAssigneeItem] = []
    due_date: Optional[date] = None
    completed_at: Optional[datetime] = None
    completed_by: Optional[str] = None
    parent_id: Optional[str] = None
    created_by: Optional[str] = None
    created_by_name: Optional[str] = None
    created_on: Optional[datetime] = None
    updated_on: Optional[datetime] = None
    
     