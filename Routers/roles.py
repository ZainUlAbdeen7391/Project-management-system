from fastapi import APIRouter, Depends, HTTPException, status
from pymysql.err import IntegrityError
from utilities.dependencies import require_permission, log_activity
from configurations.database import get_db
from schemas.rbac_schema import RoleCreate, RoleUpdate, ApiResponse
from repositories import role_repository as repo

router = APIRouter(prefix='/roles', tags=['Roles'])


# ── Create Role ────────────────────────────────────────────────────────────

@router.post("", response_model=ApiResponse, status_code=status.HTTP_201_CREATED)
async def create_role(
    payload: RoleCreate,
    cur=Depends(get_db),
    current_user: dict = Depends(require_permission("roles", "role", "create")),
):
    payload.role_slug = payload.role_slug.lower().strip()

    try:
        role_id = await repo.create_role(cur, payload, current_user["user_id"])
    except IntegrityError:
        raise HTTPException(status_code=400, detail="Role slug already exists.")

    role = await repo.get_role_by_id_any_status(cur, role_id)

    await log_activity(
        cur,
        current_user["user_id"],
        "create",
        "role",
        role_id,
        description=f"Created role '{payload.role_name}'",
        new_values=payload.model_dump(),
    )

    return {
        "success": True,
        "message": "Role created successfully",
        "data": role,
    }


# ── List All Roles ────────────────────────────────────────────────────────

@router.get("", response_model=ApiResponse)
async def list_roles(
    cur=Depends(get_db),
    current_user: dict = Depends(require_permission("roles", "role", "read")),
):
    roles = await repo.list_active_roles(cur)
    return {
        "success": True,
        "message": "Roles fetched successfully",
        "data": roles,
    }


# ── Get Single Role ──────────────────────────────────────────────────────

@router.get("/{role_id}", response_model=ApiResponse)
async def get_role(
    role_id: int,
    cur=Depends(get_db),
    current_user: dict = Depends(require_permission("roles", "role", "read")),
):
    role = await repo.get_active_role_by_id(cur, role_id)
    if not role:
        raise HTTPException(status_code=404, detail="Role not Found")

    return {
        "success": True,
        "message": "Role has successfully fetched",
        "data": role,
    }


# ── Update Role ──────────────────────────────────────────────────────────

@router.put("/{role_id}", response_model=ApiResponse)
async def update_role(
    role_id: int,
    payload: RoleUpdate,
    cur=Depends(get_db),
    current_user: dict = Depends(require_permission("roles", "role", "update")),
):
    old_role = await repo.get_active_role_by_id(cur, role_id)
    if not old_role:
        raise HTTPException(status_code=404, detail="Role not found")

    try:
        has_changes = await repo.update_role(cur, role_id, payload, current_user["user_id"])
    except IntegrityError:
        raise HTTPException(status_code=400, detail="Role slug already exists.")

    if not has_changes:
        return {
            "success": True,
            "message": "No changes detected",
            "data": old_role,
        }

    if cur.rowcount == 0:
        raise HTTPException(status_code=404, detail="Role not found and there is no changes occurred")

    updated_role = await repo.get_role_by_id_any_status(cur, role_id)

    await log_activity(
        cur, current_user["user_id"], "update", "role", role_id,
        description=f"Updated role '{updated_role['role_name']}'",
        old_values={k: old_role[k] for k in ["role_name", "role_slug", "description"]},
        new_values=payload.model_dump(exclude_unset=True),
    )

    return {
        "success": True,
        "message": "Role updated successfully",
        "data": updated_role,
    }


# ── Delete Role (soft) ──────────────────────────────────────────────────────

@router.delete("/{role_id}", response_model=ApiResponse)
async def delete_role(
    role_id: int,
    cur=Depends(get_db),
    current_user: dict = Depends(require_permission("roles", "role", "delete")),
):
    affected = await repo.soft_delete_role(cur, role_id, current_user["user_id"])
    if affected == 0:
        raise HTTPException(status_code=404, detail="Role not found.")

    await log_activity(
        cur,
        current_user["user_id"],
        "soft_delete",
        "role",
        role_id,
        description=f"Soft-deleted role id {role_id}",
    )

    return {
        "success": True,
        "message": "Role deleted successfully",
        "data": None,
    }