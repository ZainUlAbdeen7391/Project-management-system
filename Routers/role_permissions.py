from fastapi import APIRouter, Depends, HTTPException, status, Query
from typing import Optional, List
from pymysql.err import IntegrityError

from utilities.dependencies import get_db, get_current_user, require_permission, log_activity
from schemas.role_permissions import PermissionCreate, PermissionUpdate, PermissionOut
from repositories import role_permission_repository as repo

router = APIRouter(prefix="/role-permissions", tags=["Role Permissions"])


# ── Create Permission ─────────────────────────────────────────────────────────

@router.post("", response_model=PermissionOut, status_code=status.HTTP_201_CREATED)
async def create_permission(
    payload: PermissionCreate,
    cur=Depends(get_db),
    current_user: dict = Depends(require_permission("permissions", "permission", "create")),
):
    try:
        permission_id = await repo.create_permission(cur, payload)
    except IntegrityError:
        raise HTTPException(status_code=400, detail="Permission slug already exists.")

    row = await repo.get_permission_by_id(cur, permission_id)

    await log_activity(
        cur,
        user_id=current_user["user_id"],
        action="create",
        entity_type="permission",
        entity_id=permission_id,
        description=f"Created permission '{payload.permission_slug}' for role_id {payload.role_id}",
        new_values={
            "role_id": payload.role_id,
            "module_id": payload.module_id,
            "permission_name": payload.permission_name,
            "permission_slug": payload.permission_slug,
            "resource": payload.resource,
            "action": payload.action,
            "status": payload.status,
        },
    )
    return row


# ── List Permissions ──────────────────────────────────────────────────────────

@router.get("", response_model=List[PermissionOut])
async def list_permissions(
    role_id: Optional[int] = Query(None),
    module_id: Optional[int] = Query(None),
    cur=Depends(get_db),
    current_user: dict = Depends(require_permission("permissions", "permission", "read")),
):
    return await repo.list_permissions(cur, role_id=role_id, module_id=module_id)


# ── Update Permission ──────────────────────────────────────────────────────────

@router.put("/{permission_id}", response_model=PermissionOut)
async def update_permission(
    permission_id: int,
    payload: PermissionUpdate,
    cur=Depends(get_db),
    current_user: dict = Depends(require_permission("permissions", "permission", "update")),
):
    old = await repo.get_active_permission_by_id(cur, permission_id)
    if not old:
        raise HTTPException(status_code=404, detail="Permission not found.")

    try:
        has_changes = await repo.update_permission(cur, permission_id, payload)
    except IntegrityError:
        raise HTTPException(status_code=400, detail="Permission slug conflict.")

    if not has_changes:
        return old

    updated = await repo.get_permission_by_id(cur, permission_id)

    await log_activity(
        cur, current_user["user_id"], "update", "permission", permission_id,
        old_values={
            k: old[k]
            for k in ["permission_name", "permission_slug", "resource", "action", "description", "status"]
        },
        new_values=payload.model_dump(exclude_unset=True),
    )
    return updated


# ── Delete Permission (soft) ────────────────────────────────────────────────────

@router.delete("/{permission_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_permission(
    permission_id: int,
    cur=Depends(get_db),
    current_user: dict = Depends(require_permission("permissions", "permission", "delete")),
):
    row = await repo.get_permission_for_delete(cur, permission_id)
    if not row:
        raise HTTPException(status_code=404, detail=f"Permission id {permission_id} does not exist.")
    if row["deleted_on"] is not None:
        raise HTTPException(
            status_code=400,
            detail=f"Permission id {permission_id} has been soft-deleted on {row['deleted_on']}.",
        )
    if row["status"] == 0:
        raise HTTPException(
            status_code=400,
            detail=f"Permission id {permission_id} is already inactive (status=0).",
        )

    affected = await repo.soft_delete_permission(cur, permission_id)
    if affected == 0:
        raise HTTPException(status_code=409, detail="Delete failed: row was modified by another request.")

    await log_activity(
        cur,
        user_id=current_user["user_id"],
        action="soft_delete",
        entity_type="permission",
        entity_id=permission_id,
        description=f"Revoked permission '{row['permission_slug']}' from role_id {row['role_id']}",
        old_values={"status": row["status"], "deleted_on": None, "role_id": row["role_id"]},
        new_values={"status": 0, "deleted_on": "NOW()", "role_id": row["role_id"]},
    )
    return None