
_SELECT_WITH_JOINS = """
    SELECT
        p.*,
        m.module_name, m.module_slug,
        r.role_name, r.role_slug
    FROM tbl_module_role_permissions p
    LEFT JOIN tbl_modules m ON p.module_id = m.module_id AND m.deleted_on IS NULL
    LEFT JOIN tbl_roles   r ON p.role_id   = r.role_id   AND r.deleted_on IS NULL
"""


# ── Create ───────────────────────────────────────────────────────────────────

async def create_permission(cur, payload) -> int:
    """Inserts a new permission row and returns its permission_id."""
    await cur.execute(
        """
        INSERT INTO tbl_module_role_permissions
            (module_id, role_id, permission_name, permission_slug,
             resource, action, description, status, created_on, updated_on)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, NOW(), NOW())
        """,
        (
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
    await cur.execute("SELECT LAST_INSERT_ID() AS id")
    return (await cur.fetchone())["id"]


# ── Read ─────────────────────────────────────────────────────────────────────

async def get_permission_by_id(cur, permission_id: int):
    """Fetches a single permission (with module/role names) by id, including soft-deleted ones."""
    await cur.execute(
        f"{_SELECT_WITH_JOINS} WHERE p.permission_id = %s",
        (permission_id,),
    )
    return await cur.fetchone()


async def get_active_permission_by_id(cur, permission_id: int):
    """Fetches a single non-deleted permission row (raw, no joins)."""
    await cur.execute(
        "SELECT * FROM tbl_module_role_permissions WHERE permission_id = %s AND deleted_on IS NULL",
        (permission_id,),
    )
    return await cur.fetchone()


async def get_permission_for_delete(cur, permission_id: int):
    """Fetches minimal fields needed for the delete pre-checks."""
    await cur.execute(
        """
        SELECT permission_id, permission_slug, role_id, deleted_on, status
        FROM tbl_module_role_permissions
        WHERE permission_id = %s
        """,
        (permission_id,),
    )
    return await cur.fetchone()


async def list_permissions(cur, role_id: int | None, module_id: int | None):
    """Lists active permissions, optionally filtered by role_id and/or module_id."""
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


# ── Update ───────────────────────────────────────────────────────────────────

async def update_permission(cur, permission_id: int, payload) -> bool:
    """
    Applies a partial update to a permission row.
    Returns False if there were no fields to update (caller treats as no-op),
    True if the UPDATE statement executed.
    """
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


# ── Delete (soft) ────────────────────────────────────────────────────────────

async def soft_delete_permission(cur, permission_id: int) -> int:
    """Soft-deletes an active permission row. Returns affected row count."""
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