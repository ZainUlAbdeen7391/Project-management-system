from fastapi import APIRouter, Depends, HTTPException, status
from pymysql.err import IntegrityError
from utilities.dependencies import require_permission, log_activity
from configurations.database import get_db
from schemas.rbac_schema import RoleCreate, RoleOut, RoleUpdate, ApiResponse

router = APIRouter(prefix='/roles', tags=['Roles'])
@router.post("",response_model=ApiResponse,status_code=status.HTTP_201_CREATED)
async def create_role(payload: RoleCreate,cur=Depends(get_db),current_user: dict = Depends(require_permission("roles", "role", "create"))):
    try:
        payload.role_slug = payload.role_slug.lower().strip()
        await cur.execute("""
            INSERT INTO tbl_roles (
                role_name,
                role_slug,
                description,
                created_by,
                updated_by,
                created_on,
                updated_on
            )
            VALUES (%s, %s, %s, %s, %s, NOW(), NOW())
        """, (
            payload.role_name,
            payload.role_slug,
            payload.description,
            current_user["user_id"],
            current_user["user_id"]
        ))

        role_id = cur.lastrowid

        await cur.execute("""
            SELECT *
            FROM tbl_roles
            WHERE role_id = %s
        """, (role_id,))

        role = await cur.fetchone()

        await log_activity(
            cur,
            current_user["user_id"],
            "create",
            "role",
            role_id,
            description=f"Created role '{payload.role_name}'",
            new_values=payload.model_dump()
        )

        return {
            "success": True,
            "message": "Role created successfully",
            "data": role
        }

    except IntegrityError:
        raise HTTPException(
            status_code=400,
            detail="Role slug already exists."
        )
      
# Getting all roles 
  
@router.get("", response_model=ApiResponse)
async def list_roles(cur=Depends(get_db), current_user: dict=Depends(require_permission("roles", "role", "read"))):

    await cur.execute("""
        SELECT role_id, role_name, role_slug,
               description, status,
               created_by, updated_by,
               created_on, updated_on, deleted_on
        FROM tbl_roles
        WHERE deleted_on IS NULL
        ORDER BY role_id
    """)

    roles = await cur.fetchall()

    return {
        "success": True,
        "message": "Roles fetched successfully",
        "data": roles
    }

#Get Single Role

@router.get("/{role_id}", response_model=ApiResponse)
async def get_role(role_id: int, cur = Depends(get_db),  current_user: dict=Depends(require_permission("roles", "role", "read"))):
    await cur.execute("""
                      SELECT role_id,role_name, role_slug, description,status,created_by,updated_by, created_on, updated_on, deleted_on
                      FROM tbl_roles
                      WHERE role_id = %s AND deleted_on IS NULL
                      """, (role_id,))
    role = await cur.fetchone()
    if not role:
        raise HTTPException(status_code=404, detail="Role not Found")
    return {
            "success": True,
            "message": "Role has successfully fetched",
            "data": role
            }
    
#Update Role against an ID

@router.put("/{role_id}", response_model=ApiResponse)
async def update_role(role_id: int, payload: RoleUpdate, cur = Depends(get_db), current_user:dict = Depends(require_permission("roles", "role", "update"))):
    await cur.execute("""
                      SELECT role_id,role_name, role_slug, description,status,created_by,updated_by, created_on, updated_on, deleted_on
                      FROM tbl_roles
                      WHERE role_id = %s 
                      AND deleted_on IS NULL
                      """, (role_id,))
    old_role = await cur.fetchone()
    if not old_role:
        raise HTTPException(status_code=404, detail="Role not found")
    fields = []
    values = []

    if payload.role_name is not None:
        fields.append("role_name = %s")
        values.append(payload.role_name)

    if payload.role_slug is not None:
        fields.append("role_slug = %s")
        values.append(payload.role_slug)

    if payload.description is not None:
        fields.append("description = %s")
        values.append(payload.description)

    if not fields:
        return {
            "success": True,
            "message": "No changes detected",
            "data": old_role
            }

    fields.append("updated_by = %s")
    fields.append("updated_on = NOW()")

    values.extend([current_user["user_id"], role_id])

    query = f"""
        UPDATE tbl_roles
        SET {', '.join(fields)}
        WHERE role_id = %s
        AND deleted_on IS NULL
    """
    try:
        await cur.execute(query, tuple(values))
        if cur.rowcount == 0:
            raise HTTPException(status_code=404, detail="Role not found and there is no changes occurred")
        await cur.execute("SELECT * FROM tbl_roles WHERE role_id = %s", (role_id,))
        updated_role = await cur.fetchone()
        await log_activity(
            cur, current_user["user_id"], "update", "role", role_id,
            description=f"Updated role '{updated_role['role_name']}'",
            old_values={k: old_role[k] for k in ["role_name", "role_slug", "description"]},
            new_values=payload.model_dump(exclude_unset=True),
        )
        return {
                "success": True,
                "message": "Role updated successfully",
                "data": updated_role
                }
    except IntegrityError:
        raise HTTPException(status_code=400, detail="Role slug already exists.")
    
#delete Route 
@router.delete("/{role_id}", response_model=ApiResponse)
async def delete_role(
    role_id: int,
    cur=Depends(get_db),
    current_user: dict = Depends(require_permission("roles", "role", "delete"))
):
    await cur.execute("""
        UPDATE tbl_roles
        SET status = 0,
            deleted_on = NOW(),
            updated_by = %s,
            updated_on = NOW()
        WHERE role_id = %s
        AND deleted_on IS NULL
    """, (current_user["user_id"], role_id))
    if cur.rowcount == 0:
        raise HTTPException(status_code=404,detail="Role not found.")

    await log_activity(
        cur,
        current_user["user_id"],
        "soft_delete",
        "role",
        role_id,
        description=f"Soft-deleted role id {role_id}"
    )

    return {
        "success": True,
        "message": "Role deleted successfully",
        "data": None
    }
    

    
    
    
    
    


