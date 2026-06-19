#create
async def create_role(cur, payload, created_by: int) -> int:
    """Inserts a new role row and returns its role_id."""
    await cur.execute(
        """
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
        """,
        (
            payload.role_name,
            payload.role_slug,
            payload.description,
            created_by,
            created_by,
        ),
    )
    return cur.lastrowid


#listing
async def get_role_by_id_any_status(cur, role_id: int):
    """Fetches a role by id regardless of deleted/active state (used right after insert)."""
    await cur.execute(
        "SELECT * FROM tbl_roles WHERE role_id = %s",
        (role_id,),
    )
    return await cur.fetchone()


async def get_active_role_by_id(cur, role_id: int):
    """Fetches a single non-deleted role by id with full field set."""
    await cur.execute(
        """
        SELECT role_id, role_name, role_slug, description, status,
               created_by, updated_by, created_on, updated_on, deleted_on
        FROM tbl_roles
        WHERE role_id = %s AND deleted_on IS NULL
        """,
        (role_id,),
    )
    return await cur.fetchone()


async def list_active_roles(cur):
    """Lists all non-deleted roles."""
    await cur.execute(
        """
        SELECT role_id, role_name, role_slug,
               description, status,
               created_by, updated_by,
               created_on, updated_on, deleted_on
        FROM tbl_roles
        WHERE deleted_on IS NULL
        ORDER BY role_id
        """
    )
    return await cur.fetchall()


#udoate role
async def update_role(cur, role_id: int, payload, updated_by: int) -> bool:
    """
    Applies a partial update to a role row.
    Returns False if there were no fields to update (caller treats as no-op),
    True if the UPDATE statement executed (caller should check cur.rowcount).
    """
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
        return False

    fields.append("updated_by = %s")
    fields.append("updated_on = NOW()")
    values.extend([updated_by, role_id])

    query = f"""
        UPDATE tbl_roles
        SET {', '.join(fields)}
        WHERE role_id = %s
        AND deleted_on IS NULL
    """
    await cur.execute(query, tuple(values))
    return True


#delete role
async def soft_delete_role(cur, role_id: int, updated_by: int) -> int:
    """Soft-deletes a role. Returns affected row count."""
    await cur.execute(
        """
        UPDATE tbl_roles
        SET status = 0,
            deleted_on = NOW(),
            updated_by = %s,
            updated_on = NOW()
        WHERE role_id = %s
        AND deleted_on IS NULL
        """,
        (updated_by, role_id),
    )
    return cur.rowcount