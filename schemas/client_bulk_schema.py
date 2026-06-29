from pydantic import BaseModel
from typing import List, Optional

class RowImportResult(BaseModel):
    row_number: int
    client_name: str
    status: str
    client_id: Optional[str] = None
    errors: List[str] = []
    
class BulkImportConfirmResponse(BaseModel):
    success: bool
    message: str
    total_rows: int
    import_count: int
    skipped_count: int
    results: List[RowImportResult]
    
    
    
    
    
    
    