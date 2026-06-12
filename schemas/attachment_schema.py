from pydantic import BaseModel
from datetime import datetime
from typing import Optional
from enum import Enum

class EntityType(str, Enum):
    project = "project"
    task = "task"
    comment = "comment"
    
class AttachmentResponse(BaseModel):
    success: bool
    message: str
    attachment_id: int 
    entity_type:str 
    entity_id: int 
    file_name: str
    file_size: Optional[int] = None
    file_type: str
    uploaded_by: int
    created_on: Optional[datetime] = None
    
class AttachmentListItem(BaseModel):
    attachment_id: int
    entity_type: str
    entity_id: int
    file_name: str
    file_size: Optional[int] = None
    file_type: str
    file_path: str
    uploaded_by: int
    uploaded_by_name: Optional[str] = None
    created_on: Optional[datetime] = None
    
    
    

    
    