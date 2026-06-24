import os
import uuid
import aiofiles
from fastapi import UploadFile
from utilities.uuid_utils import generate_uuid7

UPLOAD_DIR = "uploads"

ALLOWED_TYPES = {
    "image/jpeg", "image/png", "image/gif", "image/webp",
    "application/pdf",
    "application/msword",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "application/vnd.ms-excel",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "text/plain",
}

MAX_FILE_SIZE = 10 * 1024 * 1024


async def _check_entity_access(cur, entity_type: str, entity_id: str, user_id: str):
    if entity_type == "project":
        await cur.execute(
            """
            SELECT project_id FROM tbl_projects 
            WHERE project_id = %s AND deleted_on IS NULL
            """, (entity_id,)
        )
        if not await cur.fetchone():
            raise ValueError("Project does not exist")
        
        await cur.execute(
            """
            SELECT member_id FROM tbl_project_members
            WHERE project_id = %s AND user_id = %s AND deleted_on IS NULL
            """, (entity_id, user_id,)
        )
        if not await cur.fetchone():
            raise ValueError("You are not authorized to attach file in this project")
        
    elif entity_type == "task":
        await cur.execute(
            """
            SELECT task_id FROM tbl_tasks
            WHERE task_id = %s AND deleted_on IS NULL
            """, (entity_id,)
        )
        if not await cur.fetchone():
            raise ValueError("Task does not exist")
        await _check_task_access(cur, entity_id, user_id)
    
    elif entity_type == "comment":
        await cur.execute(
            """SELECT task_id FROM tbl_comments
            WHERE comment_id = %s AND deleted_on IS NULL
            """, (entity_id,)
        )
        row = await cur.fetchone()
        if not row:
            raise ValueError("Comment does not exist")
        
        await _check_task_access(cur, row["task_id"], user_id)


async def _check_task_access(cur, task_id: str, user_id: str):
    #check responsible person 
    await cur.execute(
        """
        SELECT task_id FROM tbl_tasks
        WHERE task_id = %s AND is_responsible = %s AND deleted_on IS NULL
        """, (task_id, user_id,)
    )
    if await cur.fetchone():
        return
    
    # check assignees 
    await cur.execute(
        """
        SELECT id FROM tbl_task_assignees
        WHERE task_id = %s AND user_id = %s AND deleted_on IS NULL
        """, (task_id, user_id,)
    )
    if await cur.fetchone():
        return
    
    # Check project member
    await cur.execute(
        """
        SELECT pm.member_id FROM tbl_project_members pm
        INNER JOIN tbl_tasks t ON t.project_id = pm.project_id
        WHERE t.task_id = %s
          AND pm.user_id = %s
          AND t.deleted_on IS NULL
          AND pm.deleted_on IS NULL
        """,
        (task_id, user_id)
    )
    if await cur.fetchone():
        return

    raise ValueError("You are not authorized to attach files to this task")


async def upload_attachment(cur, entity_type: str, entity_id: str, file: UploadFile, user_id: str):
    #check access
    await _check_entity_access(cur, entity_type, entity_id, user_id)
    
    #validation about filetype
    if file.content_type not in ALLOWED_TYPES:
        raise ValueError(f"File type '{file.content_type}' is not allowed")
    
    contents = await file.read()
    file_size = len(contents)
    if file_size > MAX_FILE_SIZE:
        raise ValueError("Upload file under 10MB")
    
    folder = os.path.join(UPLOAD_DIR, f"{entity_type}s", str(entity_id))
    os.makedirs(folder, exist_ok=True)

    ext = os.path.splitext(file.filename)[1]
    unique_name = f"{uuid.uuid4().hex}{ext}"
    file_path = os.path.join(folder, unique_name)

    async with aiofiles.open(file_path, "wb") as f:
        await f.write(contents)

    attachment_id = generate_uuid7()
    await cur.execute(
        """
        INSERT INTO tbl_attachments
            (attachment_id, entity_type, entity_id, file_name, file_size, file_type, file_path, uploaded_by, status)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, 1)
        """,
        (
            attachment_id,     
            entity_type,            
            entity_id,              
            file.filename,          
            file_size,              
            file.content_type,      
            file_path,              
            user_id,                
        )
    )

    await cur.execute(
        """
        SELECT
            attachment_id, entity_type, entity_id, file_name,
            file_size, file_type, file_path, uploaded_by, created_on
        FROM tbl_attachments
        WHERE attachment_id = %s
        """,
        (attachment_id,)
    )
    return await cur.fetchone()


# listing attachments
async def list_attachments(cur, entity_type: str, entity_id: str, user_id: str):
    # Check access
    await _check_entity_access(cur, entity_type, entity_id, user_id)

    await cur.execute(
        """
        SELECT
            a.attachment_id, a.entity_type, a.entity_id,
            a.file_name, a.file_size, a.file_type, a.file_path,
            a.uploaded_by, u.full_name AS uploaded_by_name,
            a.created_on
        FROM tbl_attachments a
        LEFT JOIN tbl_users u ON a.uploaded_by = u.user_id
        WHERE a.entity_type = %s
          AND a.entity_id = %s
          AND a.deleted_on IS NULL
        ORDER BY a.created_on DESC
        """,
        (entity_type, entity_id)
    )
    return await cur.fetchall()


# delete attachment file
async def delete_attachment(cur, attachment_id: str, user_id: str):
    # check attachment exists
    await cur.execute(
        """
        SELECT attachment_id, file_path, uploaded_by
        FROM tbl_attachments
        WHERE attachment_id = %s AND deleted_on IS NULL
        """, (attachment_id,)
    )
    row = await cur.fetchone()
    if not row:
        raise ValueError("Attachment does not exist")
    
    if row['uploaded_by'] != user_id:
        raise ValueError("You can only delete your own attachment")
    
    await cur.execute(
        """
        UPDATE tbl_attachments
        SET deleted_on = UTC_TIMESTAMP(), status = 0
        WHERE attachment_id = %s
        """, (attachment_id,) 
    )
    
    if os.path.exists(row["file_path"]):
        os.remove(row["file_path"])