from fastapi import APIRouter, HTTPException, Depends, UploadFile, File
from configurations.database import get_db
from utilities.dependencies import require_permission
from repositories import client_bulk_repository
import schemas.client_bulk_schema as BulkImport_schemas

router = APIRouter(prefix="/client", tags=["Client"])

@router.post("/bulk-import", response_model=BulkImport_schemas.BulkImportConfirmResponse, status_code=201)
async def bulk_import_clients(
    file: UploadFile = File(...),
    cur=Depends(get_db),
    current_user=Depends(require_permission("clients", "client", "read")),
):
    if not file.filename.endswith(".csv"):
        raise HTTPException(status_code=400, detail="Only .csv files are accepted")
    try:
        raw_bytes = await file.read()
        result = await client_bulk_repository.import_csv(cur, raw_bytes, current_user["user_id"])
        return BulkImport_schemas.BulkImportConfirmResponse(
            success=True,
            message=f"Import completed. {result['import_count']} imported, {result['skipped_count']} skipped.",
            **result,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Server error: {str(e)}")
    
    