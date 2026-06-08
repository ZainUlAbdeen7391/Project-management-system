from fastapi import APIRouter, Depends, HTTPException, Query
from configurations.database import get_db
from repositories import comment_repository
from utilities.dependencies import get_current_user, log_activity
import schemas.comment_schema as Comment_schemas

router = APIRouter(prefix="/comments", tags=["Comments"])


def _build_comment_response(row: dict) -> Comment_schemas.CommentResponse:
    return Comment_schemas.CommentResponse(
        success=True,
        message="",                        # set by each endpoint
        comment_id=row["comment_id"],
        task_id=row["task_id"],
        parent_id=row["parent_id"],
        comment=row["comment"],
        author=Comment_schemas.CommentAuthor(
            user_id=row["user_id"],
            full_name=row.get("full_name"),
        ),
        created_on=row["created_on"],
        updated_on=row["updated_on"],
    )


def _build_comment_item(row: dict) -> Comment_schemas.CommentItem:
    return Comment_schemas.CommentItem(
        comment_id=row["comment_id"],
        task_id=row["task_id"],
        parent_id=row["parent_id"],
        comment=row["comment"],
        author=Comment_schemas.CommentAuthor(
            user_id=row["user_id"],
            full_name=row.get("full_name"),
        ),
        replies=[_build_comment_item(r) for r in row.get("replies", [])],
        created_on=row["created_on"],
        updated_on=row["updated_on"],
    )


# ── create comment or reply ───────────────────────────────────────────────────

@router.post("/", response_model=Comment_schemas.CommentResponse, status_code=201)
async def create_comment(
    payload: Comment_schemas.CommentCreateRequest,
    cur=Depends(get_db),
    current_user=Depends(get_current_user)
):
    try:
        row = await comment_repository.create_comment(
            cur,
            task_id=payload.task_id,
            comment=payload.comment,
            parent_id=payload.parent_id,
            user_id=current_user["user_id"],
        )
        await log_activity(
            cur=cur,
            user_id=current_user["user_id"],
            action="create",
            entity_type="comment",
            entity_id=row["comment_id"],
            description=f"{'Replied to comment' if payload.parent_id else 'Commented on'} task {payload.task_id}",
            old_values=None,
            new_values={"comment": row["comment"]}
        )
        response = _build_comment_response(row)
        response.message = "Comment created successfully"
        return response

    except ValueError as e:
        raise HTTPException(400, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(500, detail=f"Server error: {str(e)}")


# ── list comments for a task ──────────────────────────────────────────────────

@router.get("/task/{task_id}")
async def list_comments(
    task_id: int,
    cur=Depends(get_db),
    current_user=Depends(get_current_user)
):
    try:
        comments = await comment_repository.list_comments(
            cur,
            task_id=task_id,
            user_id=current_user["user_id"]
        )
        return {
            "success": True,
            "message": "Comments retrieved successfully",
            "count": len(comments),
            "data": [_build_comment_item(c) for c in comments],
        }

    except ValueError as e:
        raise HTTPException(400, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(500, detail=f"Server error: {str(e)}")


# ── update comment ────────────────────────────────────────────────────────────

@router.put("/{comment_id}", response_model=Comment_schemas.CommentResponse)
async def update_comment(
    comment_id: int,
    payload: Comment_schemas.CommentUpdateRequest,
    cur=Depends(get_db),
    current_user=Depends(get_current_user)
):
    try:
        row = await comment_repository.update_comment(
            cur,
            comment_id=comment_id,
            new_comment=payload.comment,
            user_id=current_user["user_id"]
        )
        await log_activity(
            cur=cur,
            user_id=current_user["user_id"],
            action="update",
            entity_type="comment",
            entity_id=comment_id,
            description=f"Updated comment {comment_id}",
            old_values=None,
            new_values={"comment": row["comment"]}
        )
        response = _build_comment_response(row)
        response.message = "Comment updated successfully"
        return response

    except ValueError as e:
        raise HTTPException(400, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(500, detail=f"Server error: {str(e)}")


# ── delete comment ────────────────────────────────────────────────────────────

@router.delete("/{comment_id}")
async def delete_comment(
    comment_id: int,
    cur=Depends(get_db),
    current_user=Depends(get_current_user)
):
    try:
        await comment_repository.delete_comment(
            cur,
            comment_id=comment_id,
            user_id=current_user["user_id"]
        )
        await log_activity(
            cur=cur,
            user_id=current_user["user_id"],
            action="soft_delete",
            entity_type="comment",
            entity_id=comment_id,
            description=f"Deleted comment {comment_id}"
        )
        return {
            "success": True,
            "message": "Comment deleted successfully",
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