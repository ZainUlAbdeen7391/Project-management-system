from fastapi import APIRouter, Depends, HTTPException, status, Query
from typing import Optional, List
from pymysql.err import IntegrityError
from utilities.dependencies import get_db, get_current_user, require_permission, log_activity
from schemas.role_permissions import PermissionCreate, PermissionUpdate, PermissionOut

router = APIRouter(prefix="/role-permissions", tags=["Role Permissions"])

@router.post("", response_model=PermissionOut, status_code=status.HTTP_201_CREATED)
async def create_permission(payload: PermissionCreate, cur = Depends(get_db), current_user:dict=Depends(require_permission("permissions", "permission", "create"))):
    try:
        await cur.execute("""
            INSERT INTO tbl_module_role_permissions 
            (module_id, role_id, permission_name, permission_slug, resource, action, description, status, created_on, updated_on)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, NOW(), NOW())
        """, (
            payload.module_id, payload.role_id, payload.permission_name,
            payload.permission_slug, payload.resource, payload.action,
            payload.description, payload.status
        ))

        await cur.execute("SELECT LAST_INSERT_ID() as id")
        perm_id = (await cur.fetchone())["id"]
        await cur.execute("""
            SELECT 
                p.*,
                m.module_name, m.module_slug,
                r.role_name, r.role_slug
            FROM tbl_module_role_permissions p
            LEFT JOIN tbl_modules m ON p.module_id = m.module_id
            LEFT JOIN tbl_roles r ON p.role_id = r.role_id
            WHERE p.permission_id = %s
        """, (perm_id,))
        row = await cur.fetchone()
        await log_activity(
            cur,
            user_id=current_user["user_id"],
            action="create",
            entity_type="permission",
            entity_id=perm_id,
            description=f"Created permission '{payload.permission_slug}' for role_id {payload.role_id}",
            new_values={
                "role_id": payload.role_id,
                "module_id": payload.module_id,
                "permission_name": payload.permission_name,
                "permission_slug": payload.permission_slug,
                "resource": payload.resource,
                "action": payload.action,
                "status": payload.status
            }
        )
        return row

    except IntegrityError:
        raise HTTPException(status_code=400, detail="Permission slug already exists.")

# List all permission with module and roles
@router.get("",response_model=List[PermissionOut])
async def list_permissions(role_id: Optional[int] = Query(None), module_id: Optional[int]=Query(None), cur = Depends(get_db),
                           current_user:dict = Depends(require_permission("permissions", "permission", "read"))):
    sql = """
        SELECT 
            p.*,m.module_name, m.module_slug,
            r.role_name, r.role_slug
        FROM tbl_module_role_permissions p
        LEFT JOIN tbl_modules m ON p.module_id = m.module_id AND m.deleted_on IS NULL
        LEFT JOIN tbl_roles r ON p.role_id = r.role_id AND r.deleted_on IS NULL
        WHERE p.deleted_on IS NULL
    """
    params = []
    if role_id is not None:
        sql += " AND p.role_id = %s"
        params.append(role_id)
    if module_id is not None:
        sql += " AND p.module_id = %s"
        params.append(module_id)
    sql += " ORDER BY p.permission_id"

    await cur.execute(sql, tuple(params))
    return await cur.fetchall()

#Update the permission against id

@router.put("/{permission_id}", response_model=PermissionOut)
async def update_permission(
    permission_id: int,
    payload: PermissionUpdate,
    cur= Depends(get_db),
    current_user: dict = Depends(require_permission("permissions", "permission", "update"))
):
    await cur.execute("SELECT * FROM tbl_module_role_permissions WHERE permission_id = %s AND deleted_on IS NULL", (permission_id,))
    old = await cur.fetchone()
    if not old:
        raise HTTPException(status_code=404, detail="Permission not found.")

    fields = []
    values = []
    if payload.permission_name is not None:
        fields.append("permission_name = %s"); 
        values.append(payload.permission_name)
    if payload.permission_slug is not None:
        fields.append("permission_slug = %s"); 
        values.append(payload.permission_slug)
    if payload.resource is not None:
        fields.append("resource = %s"); 
        values.append(payload.resource)
    if payload.action is not None:
        fields.append("action = %s"); 
        values.append(payload.action)
    if payload.description is not None:
        fields.append("description = %s"); 
        values.append(payload.description)
    if payload.status is not None:
        fields.append("status = %s"); 
        values.append(payload.status)

    if not fields:
        return old

    values.append(permission_id)
    sql = f"UPDATE tbl_module_role_permissions SET {', '.join(fields)}, updated_on = NOW() WHERE permission_id = %s AND deleted_on IS NULL"

    try:
        await cur.execute(sql, tuple(values))
        await cur.execute("""
            SELECT p.*, m.module_name, m.module_slug, r.role_name, r.role_slug
            FROM tbl_module_role_permissions p
            LEFT JOIN tbl_modules m ON p.module_id = m.module_id
            LEFT JOIN tbl_roles r ON p.role_id = r.role_id
            WHERE p.permission_id = %s
        """, (permission_id,))
        updated = await cur.fetchone()

        await log_activity(
            cur, current_user["user_id"], "update", "permission", permission_id,
            old_values={k: old[k] for k in ["permission_name","permission_slug","resource","action","description","status"]},
            new_values=payload.model_dump(exclude_unset=True)
        )
        return updated
    except IntegrityError:
        raise HTTPException(status_code=400, detail="Permission slug conflict.")


# Delete permission soft deleted  
@router.delete("/{permission_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_permission(permission_id: int,cur = Depends(get_db),current_user: dict = Depends(require_permission("permissions", "permission", "delete"))):
    await cur.execute(
        "SELECT permission_id, permission_slug, role_id, deleted_on, status "
        "FROM tbl_module_role_permissions WHERE permission_id = %s",
        (permission_id,)
    )
    row = await cur.fetchone()
    if not row:
        raise HTTPException(status_code=404,detail=f"Permission id {permission_id} does not exist.")
    if row["deleted_on"] is not None:
        raise HTTPException(status_code=400,detail=f"Permission id {permission_id} has been soft-deleted on {row['deleted_on']}.")
    if row["status"] == 0:
        raise HTTPException(status_code=400,detail=f"Permission id {permission_id} is already inactive (status=0).")
    await cur.execute("""
        UPDATE tbl_module_role_permissions 
        SET 
            deleted_on = NOW(), 
            updated_on = NOW(), 
            status = 0
        WHERE permission_id = %s 
          AND deleted_on IS NULL 
          AND status = 1
    """, (permission_id,))

    if cur.rowcount == 0:
        raise HTTPException(status_code=409,detail="Delete failed: row was modified by another request.")
    await log_activity(
        cur,
        user_id=current_user["user_id"],
        action="soft_delete",
        entity_type="permission",
        entity_id=permission_id,
        description=f"Revoked permission '{row['permission_slug']}' from role_id {row['role_id']}",
        old_values={"status": row["status"],"deleted_on": None,"role_id": row["role_id"]},
        new_values={"status": 0,"deleted_on": "NOW()","role_id": row["role_id"]}
    )
    return None














    
        
        
