from fastapi import APIRouter, Depends, HTTPException, Query
from configurations.database import get_db
from repositories import project_repository
from utilities.dependencies import get_current_user, require_permission, log_activity
import schemas.project_schema as Project_schemas

router = APIRouter(prefix="/projects", tags=["Projects"])

#create project
@router.post("/", response_model=Project_schemas.ProjectResponse, status_code=201)
async def create_project(payload: Project_schemas.ProjectCreateRequest,cur=Depends(get_db),current_user=Depends(get_current_user),):
    try:
        row = await project_repository.create_project(cur, payload, current_user["user_id"])
        return Project_schemas.ProjectResponse(
            success=True,
            message="Project created successfully",
            project_id=row["project_id"],
            project_name=row["project_name"],
            description=row["description"],
            project_type=row["project_type"],
            client_id=row["client_id"],
            estimated_cost=row["estimated_cost"],
            due_date=row["due_date"],
            start_date=row["start_date"],
            end_date=row["end_date"],
            status=row["status"],     
            created_by=row["created_by"],
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

#listing projects
@router.get("/")
async def get_projects(status: Project_schemas.ProjectStatus | None = Query(None),project_type: Project_schemas.ProjectType | None = Query(None),
                       cur=Depends(get_db),current_user=Depends(require_permission("projects", "project", "read")),):
    projects = await project_repository.list_projects(
        cur,
        status=status.value if status else None,
        project_type=project_type.value if project_type else None,
    )
    return {
        "success": True,
        "message": "Projects retrieved successfully",
        "count": len(projects),
        "data": projects,
    }

#update project API Endpoint
@router.put("/{project_id}", response_model=Project_schemas.ProjectResponse)
async def update_project(project_id: int,payload: Project_schemas.ProjectUpdateRequest,
                        cur=Depends(get_db),
                        current_user=Depends(require_permission("projects", "project", "update")),):
    try:
        row = await project_repository.update_project(cur, project_id, payload)
        await log_activity(
            cur=cur,
            user_id=current_user["user_id"],
            action="update",
            entity_type="project",
            entity_id=project_id,
            description=f"Updated project '{row['project_name']}'",
            old_values=None,
            new_values={"project_name": row["project_name"], "status": row["status"]},
        )
        return Project_schemas.ProjectResponse(
            success=True,
            message="Project updated successfully",
            project_id=row["project_id"],
            project_name=row["project_name"],
            description=row["description"],
            project_type=row["project_type"],
            client_id=row["client_id"],
            estimated_cost=row["estimated_cost"],
            due_date=row["due_date"],
            start_date=row["start_date"],
            end_date=row["end_date"],
            status=row["status"],
            created_by=row["created_by"],
            created_on=row["created_on"],
            updated_on=row["updated_on"],
        )
    except ValueError as e:
        raise HTTPException(400, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(500, detail=f"Server error: {str(e)}")

#delete project from tbl_project_memebers(soft deletion)
@router.delete("/{project_id}")
async def delete_project(project_id: int,cur=Depends(get_db),current_user=Depends(require_permission("projects", "project", "delete")),):
    try:
        await project_repository.delete_project(cur, project_id)
        await log_activity(
            cur=cur,
            user_id=current_user["user_id"],
            action="soft_delete",
            entity_type="project",
            entity_id=project_id,
            description=f"Soft-deleted project id {project_id}",
        )
        return {"success": True, "message": "Project deleted successfully", "data": None}
    except ValueError as e:
        raise HTTPException(400, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(500, detail=f"Server error: {str(e)}")

#assign member to a specific project
@router.post(
    "/{project_id}/members",
    response_model=Project_schemas.ProjectMemberResponse
)
async def assign_project_members(project_id: int,payload: Project_schemas.ProjectMemberCreateRequest,cur=Depends(get_db),
                            current_user=Depends(require_permission("projects","project","manage_members")),):
    try:
        inserted_count = await project_repository.assign_project_members(
            cur=cur,
            project_id=project_id,
            member_ids=payload.members,
            manager_ids=payload.project_managers,
        )

        await log_activity(
            cur=cur,
            user_id=current_user["user_id"],
            action="create",
            entity_type="project_member",
            entity_id=project_id,
            description=(
                f"Assigned members {payload.members} "
                f"and managers {payload.project_managers} "
                f"to project {project_id}"
            ),
        )

        return Project_schemas.ProjectMemberResponse(
            success=True,
            message=f"{inserted_count} users assigned successfully",
            project_id=project_id,
            assigned_count=inserted_count,
            members=payload.members,
            project_managers=payload.project_managers,
        )

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Server error: {str(e)}"
        )
    
    
    

    
    