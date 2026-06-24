from fastapi import APIRouter, Depends, HTTPException, Query
from configurations.database import get_db
from repositories import task_repository
from utilities.dependencies import get_current_user, require_permission, log_activity
import schemas.task_schema as Task_schemas

router = APIRouter(prefix="/tasks", tags=["Tasks"])


def _build_task_response(row: dict, assignees: list[dict]) -> dict:
    return {
        **row,
        "assignees": [
            Task_schemas.TaskAssigneeItem(
                id=a["id"],
                user_id=a["user_id"],
                full_name=a.get("full_name"),
            )
            for a in assignees
        ],
    }


@router.post("/", response_model=Task_schemas.TaskResponse, status_code=201)
async def create_task(payload: Task_schemas.TaskCreateRequest,cur=Depends(get_db),current_user=Depends(require_permission("tasks", "task", "create"))
):
    try:
        row, assignees = await task_repository.create_task(cur, payload, current_user["user_id"])
        await log_activity(
            cur=cur,
            user_id=current_user["user_id"],
            action="create",
            entity_type="task",
            entity_id=row["task_id"],
            description=f"Created task '{row['title']}'",
            old_values=None,
            new_values={"title": row["title"], "status": row["status"]}
        )
        return Task_schemas.TaskResponse(
            success=True,
            message="Task created successfully",
            **_build_task_response(row, assignees)
        )
    except ValueError as e:
        raise HTTPException(400, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(500, detail=f"Server error: {str(e)}")


from typing import List

@router.get("/")
async def list_tasks(project_id: str | None = Query(None),status: Task_schemas.TaskStatus | None = Query(None),
                    priority: Task_schemas.TaskPriority | None = Query(None),assignee_user_ids: List[str] | None = Query(None),
                    cur=Depends(get_db),current_user=Depends(require_permission("tasks", "task", "read"))):
    tasks = await task_repository.list_tasks(
        cur,
        project_id=project_id,
        status=status.value if status else None,
        priority=priority.value if priority else None,
        assignee_user_ids=assignee_user_ids,        
    )
    return {
        "success": True,
        "message": "Tasks retrieved successfully",
        "count": len(tasks),
        "data": [
            {
                **row,
                "assignees": [
                    {"id": a["id"], "user_id": a["user_id"], "full_name": a.get("full_name")}
                    for a in assignees
                ],
            }
            for row, assignees in tasks
        ],
    }
@router.put("/{task_id}", response_model=Task_schemas.TaskResponse)
async def update_task(task_id: str,payload: Task_schemas.TaskUpdateRequest,cur=Depends(get_db),
                      current_user=Depends(require_permission("tasks", "task", "update"))):
    try:
        row, assignees = await task_repository.update_task(
            cur, 
            task_id, 
            payload, 
            current_user["user_id"]
        )
        await log_activity(
            cur=cur,
            user_id=current_user["user_id"],
            action="update",
            entity_type="task",
            entity_id=task_id,
            description=f"Updated task '{row['title']}'",
            old_values=None,
            new_values={"title": row["title"], "status": row["status"]}
        )
        return Task_schemas.TaskResponse(
            success=True,
            message="Task updated successfully",
            **_build_task_response(row, assignees)
        )
    except ValueError as e:
        raise HTTPException(400, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(500, detail=f"Server error: {str(e)}")

    
@router.delete("/{task_id}")
async def delete_task(task_id: str,cur=Depends(get_db),current_user=Depends(require_permission("tasks", "task", "delete"))):
    try:
        await task_repository.delete_task(cur, task_id)
        await log_activity(
            cur=cur,
            user_id=current_user["user_id"],
            action="soft_delete",
            entity_type="task",
            entity_id=task_id,
            description=f"Soft-deleted task id {task_id}"
        )
        return {
            "success": True,
            "message": "Task deleted successfully",
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