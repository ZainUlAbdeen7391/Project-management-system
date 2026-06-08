import schemas.project_schema as Project_schemas
from datetime import datetime, UTC
from typing import List

async def create_project(cur, payload: Project_schemas.ProjectCreateRequest, created_by: int):
    if payload.client_id is not None:
        await cur.execute(
            """
            SELECT client_id
            FROM tbl_client
            WHERE client_id = %s
              AND deleted_on IS NULL
            LIMIT 1
            """,
            (payload.client_id,),
        )
        if not await cur.fetchone():
            raise ValueError("Client does not exist")

    cost = float(payload.estimated_cost) if payload.estimated_cost is not None else None

    await cur.execute(
        """
        INSERT INTO tbl_projects
            (project_name, description, project_type, client_id,
             estimated_cost, due_date, start_date, status, created_by)
        VALUES (%s, %s, %s, %s, %s, %s, UTC_TIMESTAMP(), 'active', %s)
        """,
        (
            payload.project_name,
            payload.description,
            payload.project_type.value,
            payload.client_id,
            cost,
            payload.due_date,
            created_by,
        ),
    )

    project_id = getattr(cur, "lastrowid", None)
    if not project_id:
        await cur.execute("SELECT LAST_INSERT_ID() AS id")
        result = await cur.fetchone()
        project_id = result["id"] if result else None
    if not project_id:
        raise RuntimeError("Failed to retrieve project_id after insert")

    await cur.execute(
        """
        SELECT project_id, project_name, description, project_type, client_id,
               estimated_cost, due_date, start_date, end_date,
               status, created_by, created_on, updated_on
        FROM tbl_projects
        WHERE project_id = %s
        """,
        (project_id,),
    )
    return await cur.fetchone()


# ── List Projects ───────────────────────────────────────────────────────────

async def list_projects(cur, status: str = None, project_type: str = None):
    query = """
        SELECT
            p.project_id,
            p.project_name,
            p.description,
            p.project_type,
            p.client_id,
            c.client_name,
            p.estimated_cost,
            p.due_date,
            p.start_date,
            p.end_date,
            p.status,
            p.created_by,
            u.full_name AS created_by_name,
            p.created_on,
            p.updated_on
        FROM tbl_projects p
        LEFT JOIN tbl_client c ON p.client_id = c.client_id
        LEFT JOIN tbl_users  u ON p.created_by = u.user_id
        WHERE p.deleted_on IS NULL
    """
    params = []

    if status:
        query += " AND p.status = %s"
        params.append(status)
    if project_type:
        query += " AND p.project_type = %s"
        params.append(project_type)

    query += " ORDER BY p.project_id DESC"
    await cur.execute(query, tuple(params))
    return await cur.fetchall()


#Update Project function

async def update_project(cur, project_id: int, payload: Project_schemas.ProjectUpdateRequest):
    await cur.execute(
        """
        SELECT project_id, status, start_date, end_date
        FROM tbl_projects
        WHERE project_id = %s AND deleted_on IS NULL
        """,
        (project_id,),
    )
    project = await cur.fetchone()
    if not project:
        raise ValueError("Project does not exist")

    if payload.client_id is not None:
        await cur.execute(
            """
            SELECT client_id
            FROM tbl_client
            WHERE client_id = %s AND deleted_on IS NULL
            LIMIT 1
            """,
            (payload.client_id,),
        )
        if not await cur.fetchone():
            raise ValueError("Client does not exist")

    fields = []
    values = []

    if payload.project_name is not None:
        fields.append("project_name = %s")
        values.append(payload.project_name)
    if payload.description is not None:
        fields.append("description = %s")
        values.append(payload.description)
    if payload.project_type is not None:
        fields.append("project_type = %s")
        values.append(payload.project_type.value)
    if payload.client_id is not None:
        fields.append("client_id = %s")
        values.append(payload.client_id)
    if payload.estimated_cost is not None:
        fields.append("estimated_cost = %s")
        values.append(float(payload.estimated_cost))
    if payload.due_date is not None:
        fields.append("due_date = %s")
        values.append(payload.due_date)
    if payload.status is not None:
        new_status = payload.status.value

        if new_status == "active" and project["start_date"] is None:
            fields.append("start_date = UTC_TIMESTAMP()")
        if new_status == "completed" and project["end_date"] is None:
            fields.append("end_date = UTC_TIMESTAMP()")
        fields.append("status = %s")
        values.append(new_status)

    if not fields:
        raise ValueError("No fields provided for update")

    values.append(project_id)
    sql = f"""
        UPDATE tbl_projects
        SET {', '.join(fields)}
        WHERE project_id = %s AND deleted_on IS NULL
    """
    await cur.execute(sql, tuple(values))

    await cur.execute(
        """
        SELECT project_id, project_name, description, project_type, client_id,
               estimated_cost, due_date, start_date, end_date,
               status, created_by, created_on, updated_on
        FROM tbl_projects
        WHERE project_id = %s
        """,
        (project_id,),
    )
    return await cur.fetchone()


#Delete Project 

async def delete_project(cur, project_id: int):
    await cur.execute(
        """
        SELECT project_id
        FROM tbl_projects
        WHERE project_id = %s AND deleted_on IS NULL
        """,
        (project_id,),
    )
    if not await cur.fetchone():
        raise ValueError("Project not found")

    await cur.execute(
        """
        UPDATE tbl_projects
        SET deleted_on = UTC_TIMESTAMP()
        WHERE project_id = %s
        """,
        (project_id,),
    )


#Assign Members to Project

from typing import List

async def assign_project_members(
    cur,
    project_id: int,
    member_ids: List[int],
    manager_ids: List[int],
) -> int:

    # Check project exists
    await cur.execute(
        """
        SELECT project_id
        FROM tbl_projects
        WHERE project_id=%s
        AND deleted_on IS NULL
        """,
        (project_id,)
    )

    if not await cur.fetchone():
        raise ValueError("Project not found")

    # Managers must also be members
    all_member_ids = list(set(member_ids + manager_ids))

    # Validate users
    for user_id in all_member_ids:
        await cur.execute(
            """
            SELECT user_id
            FROM tbl_users
            WHERE user_id=%s
            """,
            (user_id,)
        )

        if not await cur.fetchone():
            raise ValueError(f"User {user_id} not found")

    inserted = 0

    # Optional: Clear old assignments and replace them
    await cur.execute(
        """
        DELETE FROM tbl_project_members
        WHERE project_id=%s
        """,
        (project_id,)
    )

    # Insert all members
    for user_id in all_member_ids:

        is_manager = 1 if user_id in manager_ids else 0

        await cur.execute(
            """
            INSERT INTO tbl_project_members
            (
                project_id,
                user_id,
                is_project_manager,
                created_on
            )
            VALUES
            (
                %s,
                %s,
                %s,
                NOW()
            )
            """,
            (
                project_id,
                user_id,
                is_manager,
            )
        )

        inserted += 1

    await cur.connection.commit()

    return inserted