from utilities.uuid_utils import generate_uuid7
_SELECT_WITH_JOINS = """
    SELECT
        p.*,
        m.module_name, m.module_slug,
        r.role_name, r.role_slug
    FROM tbl_module_role_permissions p
    LEFT JOIN tbl_modules m ON p.module_id = m.module_id AND m.deleted_on IS NULL
    LEFT JOIN tbl_roles   r ON p.role_id   = r.role_id   AND r.deleted_on IS NULL
"""


#create
async def create_permission(cur, payload) -> str:
    permission_id = generate_uuid7()
    await cur.execute(
        """
        INSERT INTO tbl_module_role_permissions
            (permission_id, module_id, role_id, permission_name, permission_slug,
             resource, action, description, status, created_on, updated_on)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, NOW(), NOW())
        """,
        (
            permission_id,
            payload.module_id,
            payload.role_id,
            payload.permission_name,
            payload.permission_slug,
            payload.resource,
            payload.action,
            payload.description,
            payload.status,
        ),
    )
    return permission_id

#Listing
async def get_permission_by_id(cur, permission_id: str):
    """Fetches a single permission (with module/role names) by id, including soft-deleted ones."""
    await cur.execute(
        f"{_SELECT_WITH_JOINS} WHERE p.permission_id = %s",
        (permission_id,),
    )
    return await cur.fetchone()


async def get_active_permission_by_id(cur, permission_id: str):
    await cur.execute(
        "SELECT * FROM tbl_module_role_permissions WHERE permission_id = %s AND deleted_on IS NULL",
        (permission_id,),
    )
    return await cur.fetchone()


async def get_permission_for_delete(cur, permission_id: str):
    await cur.execute(
        """
        SELECT permission_id, permission_slug, role_id, deleted_on, status
        FROM tbl_module_role_permissions
        WHERE permission_id = %s
        """,
        (permission_id,),
    )
    return await cur.fetchone()


async def list_permissions(cur, role_id: str | None, module_id: str | None):
    sql = f"{_SELECT_WITH_JOINS} WHERE p.deleted_on IS NULL"
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


#update function
async def update_permission(cur, permission_id: str, payload) -> bool:

    fields = []
    values = []

    if payload.permission_name is not None:
        fields.append("permission_name = %s")
        values.append(payload.permission_name)
    if payload.permission_slug is not None:
        fields.append("permission_slug = %s")
        values.append(payload.permission_slug)
    if payload.resource is not None:
        fields.append("resource = %s")
        values.append(payload.resource)
    if payload.action is not None:
        fields.append("action = %s")
        values.append(payload.action)
    if payload.description is not None:
        fields.append("description = %s")
        values.append(payload.description)
    if payload.status is not None:
        fields.append("status = %s")
        values.append(payload.status)

    if not fields:
        return False

    values.append(permission_id)
    sql = (
        f"UPDATE tbl_module_role_permissions "
        f"SET {', '.join(fields)}, updated_on = NOW() "
        f"WHERE permission_id = %s AND deleted_on IS NULL"
    )
    await cur.execute(sql, tuple(values))
    return True

#delete
async def soft_delete_permission(cur, permission_id: str) -> str:
    await cur.execute(
        """
        UPDATE tbl_module_role_permissions
        SET deleted_on = NOW(), updated_on = NOW(), status = 0
        WHERE permission_id = %s
          AND deleted_on IS NULL
          AND status = 1
        """,
        (permission_id,),
    )
    return cur.rowcount