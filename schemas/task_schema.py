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
    project_id: int
    title: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    status: TaskStatus = TaskStatus.todo
    priority: TaskPriority = TaskPriority.medium
    is_responsible: int               
    assignees: list[int] = Field(..., min_length=1)
    due_date: Optional[date] = None
    parent_id: Optional[int] = None   # for sub-tasks

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
    is_responsible: Optional[int] = None
    assignees: Optional[list[int]] = Field(default=None, min_length=1)
    due_date: Optional[date] = None
    parent_id: Optional[int] = None

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
    id: int
    user_id: int
    full_name: Optional[str] = None


class TaskResponse(BaseModel):
    success: bool
    message: str
    task_id: int
    project_id: int
    title: str
    description: Optional[str] = None
    status: str
    priority: str
    is_responsible: int
    assignees: list[TaskAssigneeItem] = []
    due_date: Optional[date] = None
    completed_at: Optional[datetime] = None
    completed_by: Optional[int] = None
    parent_id: Optional[int] = None
    created_by: Optional[int] = None
    created_on: Optional[datetime] = None
    updated_on: Optional[datetime] = None


class TaskListItem(BaseModel):
    task_id: int
    project_id: int
    project_name: Optional[str] = None
    title: str
    description: Optional[str] = None
    status: str
    priority: str
    is_responsible: int
    responsible_name: Optional[str] = None
    assignees: list[TaskAssigneeItem] = []
    due_date: Optional[date] = None
    completed_at: Optional[datetime] = None
    completed_by: Optional[int] = None
    parent_id: Optional[int] = None
    created_by: Optional[int] = None
    created_by_name: Optional[str] = None
    created_on: Optional[datetime] = None
    updated_on: Optional[datetime] = None
    
     