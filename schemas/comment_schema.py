from pydantic import BaseModel, Field, field_validator
from datetime import datetime
from typing import Optional, List


class CommentCreateRequest(BaseModel):
    task_id: int
    comment: str = Field(..., min_length=1)
    parent_id: Optional[int] = None

    @field_validator("parent_id", mode="before")
    @classmethod
    def coerce_null_string(cls, v):
        
        if v is None:
            return None
        if isinstance(v, str) and v.strip().lower() in ("null", "none", ""):
            return None
        if isinstance(v, int) and v == 0:
            return None
        return v
    
class CommentUpdateRequest(BaseModel):
    comment: str = Field(..., min_length=1)
    
class CommentAuthor(BaseModel):
    user_id: int
    full_name: Optional[str] = None
    
class CommentItem(BaseModel):
    comment_id: int
    task_id: int 
    parent_id: Optional[int] = None
    comment: str
    author: CommentAuthor
    replies: List["CommentItem"] = []
    created_on: Optional[datetime] = None 
    updated_on: Optional[datetime] = None
    
    
    
CommentItem.model_rebuild()


class CommentResponse(BaseModel):
    success: bool
    message: str
    comment_id: int
    task_id: int
    parent_id: Optional[int] = None
    comment: str
    author: CommentAuthor
    created_on: Optional[datetime] = None
    updated_on: Optional[datetime] = None
    

    