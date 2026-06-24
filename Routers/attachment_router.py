from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from configurations.database import get_db
from repositories import attachment_repository
from utilities.dependencies import get_current_user, log_activity
import schemas.attachment_schema as Attachment_schemas

router = APIRouter(prefix="/attachments", tags=["Attachments"])


#upload attachment endpoint 
@router.post("/{entity_type}/{entity_id}", response_model=Attachment_schemas.AttachmentResponse, status_code=201)
async def upload_attachment(entity_type: Attachment_schemas.EntityType,entity_id: str,file: UploadFile=File(...,),
                            cur=Depends(get_db),current_user = Depends(get_current_user)):
    try:
        row = await attachment_repository.upload_attachment(
            cur, 
            entity_type=entity_type.value,
            entity_id=entity_id, 
            file=file, 
            user_id=current_user["user_id"]
            )
        await log_activity(
            cur=cur,
            user_id=current_user["user_id"],
            action="create",
            entity_type="attachment",
            entity_id=row["attachment_id"],
            description=f"Uploaded '{row['file_name']}' to {entity_type.value} {entity_id}",
            old_values=None,
            new_values={"file_name": row["file_name"], "file_type": row["file_type"]}
        )
        
        return Attachment_schemas.AttachmentResponse(
            success=True,
            message="File uploaded successfully",
            attachment_id=row["attachment_id"],
            entity_type=row["entity_type"],
            entity_id=row["entity_id"],
            file_name=row["file_name"],
            file_size=row["file_size"],
            file_type=row["file_type"],
            file_path=row["file_path"],
            uploaded_by=row["uploaded_by"],
            created_on=row["created_on"],
        )
    except ValueError as e:
        raise HTTPException(400, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(500, detail=f"Server error: {str(e)}")
    
    
#listing all 
@router.get("/{entity_type}/{entity_id}")
async def list_attachment(entity_type: Attachment_schemas.EntityType,entity_id: str, cur=Depends(get_db),current_user=Depends(get_current_user)):
    try:
        attachments = await attachment_repository.list_attachments(
            cur, entity_type=entity_type.value, entity_id=entity_id, user_id=current_user["user_id"],
        )
        return{
            "success": True,
            "message": "Attachments retrieved successfully",
            "count": len(attachments),
            "data": attachments,
        }
    except ValueError as e:
        raise HTTPException(400, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(500, detail=f"Server error: {str(e)}")
    
#delete attachment from tbl_attachments
@router.delete("/{attachment_id}")
async def delete_attachment(attachment_id: str,cur=Depends(get_db),current_user=Depends(get_current_user)):
    try:
        await attachment_repository.delete_attachment(
            cur,
            attachment_id=attachment_id,
            user_id=current_user["user_id"]
        )
        await log_activity(
            cur=cur,
            user_id=current_user["user_id"],
            action="delete",
            entity_type="attachment",
            entity_id=attachment_id,
            description=f"Deleted attachment {attachment_id}"
        )
        return {
            "success": True,
            "message": "Attachment deleted successfully",
            "data": None,
        }
    except ValueError as e:
        raise HTTPException(400, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(500, detail=f"Server error: {str(e)}")
    
    