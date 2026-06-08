import schemas.task_schema as Task_schemas



async def _fetch_task_assignees(cur, task_id: int) -> list[dict]:
    await cur.execute(
        """
        SELECT ta.id, ta.user_id, u.full_name
        FROM tbl_task_assignees ta
        LEFT JOIN tbl_users u ON ta.user_id = u.user_id
        WHERE ta.task_id = %s AND ta.deleted_on IS NULL
        """,
        (task_id,)
    )
    return await cur.fetchall()


async def _verify_user(cur, user_id: int, label: str = "User"):
    await cur.execute(
        "SELECT user_id FROM tbl_users WHERE user_id = %s",
        (user_id,)
    )
    if not await cur.fetchone():
        raise ValueError(f"{label} with id {user_id} not found")



async def create_task(cur, payload: Task_schemas.TaskCreateRequest, created_by: int):
    await cur.execute(
        "SELECT project_id FROM tbl_projects WHERE project_id = %s AND deleted_on IS NULL",
        (payload.project_id,)
    )
    if not await cur.fetchone():
        raise ValueError("Project does not exist")

    await _verify_user(cur, payload.is_responsible, "Responsible user")

    for uid in payload.assignees:
        await _verify_user(cur, uid, "Assignee")

    if payload.parent_id is not None:
        await cur.execute(
            "SELECT task_id FROM tbl_tasks WHERE task_id = %s AND deleted_on IS NULL",
            (payload.parent_id,)
        )
        if not await cur.fetchone():
            raise ValueError("Parent task does not exist")

    await cur.execute(
        """
        INSERT INTO tbl_tasks
            (project_id, title, description, status, priority,
             is_responsible, assignees, due_date, parent_id, created_by)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """,
        (
            payload.project_id,
            payload.title,
            payload.description,
            payload.status.value,
            payload.priority.value,
            payload.is_responsible,
            payload.assignees[0],
            payload.due_date,
            payload.parent_id,
            created_by,
        )
    )

    task_id = getattr(cur, "lastrowid", None)
    if not task_id:
        await cur.execute("SELECT LAST_INSERT_ID() as id")
        result = await cur.fetchone()
        task_id = result["id"] if result else None

    if not task_id:
        raise RuntimeError("Failed to retrieve task_id after insert")

    for uid in payload.assignees:
        await cur.execute(
            """
            INSERT INTO tbl_task_assignees (task_id, user_id, deleted_on)
            VALUES (%s, %s, NULL)
            ON DUPLICATE KEY UPDATE
                deleted_on = NULL,
                updated_on = UTC_TIMESTAMP()
            """,
            (task_id, uid)
        )

    await cur.execute(
        """
        SELECT
            task_id, project_id, title, description, status, priority,
            is_responsible, due_date, completed_at, completed_by,
            parent_id, created_by, created_on
        FROM tbl_tasks
        WHERE task_id = %s
        """,
        (task_id,)
    )
    row = await cur.fetchone()
    assignees = await _fetch_task_assignees(cur, task_id)
    return row, assignees



async def list_tasks(
    cur,
    project_id: int = None,
    status: str = None,
    priority: str = None,
    assignee_user_ids: list[int] = None,
):
    query = """
        SELECT
            t.task_id,
            t.project_id,
            p.project_name,
            t.title,
            t.description,
            t.status,
            t.priority,
            t.is_responsible,
            r.full_name AS responsible_name,
            t.due_date,
            t.completed_at,
            t.completed_by,
            t.parent_id,
            t.created_by,
            cb.full_name AS created_by_name,
            t.created_on,
            t.updated_on
        FROM tbl_tasks t
        LEFT JOIN tbl_projects p  ON t.project_id     = p.project_id
        LEFT JOIN tbl_users r     ON t.is_responsible = r.user_id
        LEFT JOIN tbl_users cb    ON t.created_by     = cb.user_id
        WHERE t.deleted_on IS NULL
    """

    params = []

    if project_id is not None:
        query += " AND t.project_id = %s"
        params.append(project_id)

    if status:
        query += " AND t.status = %s"
        params.append(status)

    if priority:
        query += " AND t.priority = %s"
        params.append(priority)

    if assignee_user_ids:
        placeholders = ", ".join(["%s"] * len(assignee_user_ids))
        query += f"""
            AND t.task_id IN (
                SELECT task_id FROM tbl_task_assignees
                WHERE user_id IN ({placeholders}) AND deleted_on IS NULL
            )
        """
        params.extend(assignee_user_ids)

    query += " ORDER BY t.task_id DESC"

    await cur.execute(query, tuple(params))
    tasks = await cur.fetchall()

    result = []
    for task in tasks:
        assignees = await _fetch_task_assignees(cur, task["task_id"])
        result.append((task, assignees))

    return result



async def update_task(cur, task_id: int, payload: Task_schemas.TaskUpdateRequest):
    # Verify task exists
    await cur.execute(
        "SELECT task_id FROM tbl_tasks WHERE task_id = %s AND deleted_on IS NULL",
        (task_id,)
    )
    if not await cur.fetchone():
        raise ValueError("Task does not exist")

    if payload.is_responsible is not None:
        await _verify_user(cur, payload.is_responsible, "Responsible user")

    if payload.assignees is not None:
        for uid in payload.assignees:
            await _verify_user(cur, uid, "Assignee")

    if payload.parent_id is not None:
        await cur.execute(
            "SELECT task_id FROM tbl_tasks WHERE task_id = %s AND deleted_on IS NULL",
            (payload.parent_id,)
        )
        if not await cur.fetchone():
            raise ValueError("Parent task does not exist")

    fields = []
    values = []

    if payload.title is not None:
        fields.append("title = %s")
        values.append(payload.title)
    if payload.description is not None:
        fields.append("description = %s")
        values.append(payload.description)
    if payload.status is not None:
        fields.append("status = %s")
        values.append(payload.status.value)
        if payload.status == Task_schemas.TaskStatus.completed:
            fields.append("completed_at = UTC_TIMESTAMP()")
        else:
            fields.append("completed_at = NULL")
    if payload.priority is not None:
        fields.append("priority = %s")
        values.append(payload.priority.value)
    if payload.is_responsible is not None:
        fields.append("is_responsible = %s")
        values.append(payload.is_responsible)
    if payload.assignees is not None:
        fields.append("assignees = %s")
        values.append(payload.assignees[0])
    if payload.due_date is not None:
        fields.append("due_date = %s")
        values.append(payload.due_date)
    if payload.parent_id is not None:
        fields.append("parent_id = %s")
        values.append(payload.parent_id)

    if not fields:
        raise ValueError("No fields provided for update")

    values.append(task_id)

    sql = f"UPDATE tbl_tasks SET {', '.join(fields)} WHERE task_id = %s AND deleted_on IS NULL"
    await cur.execute(sql, tuple(values))

    if payload.assignees is not None:
        await cur.execute(
            """
            UPDATE tbl_task_assignees
            SET deleted_on = UTC_TIMESTAMP()
            WHERE task_id = %s AND deleted_on IS NULL
            """,
            (task_id,)
        )
        for uid in payload.assignees:
            await cur.execute(
                """
                INSERT INTO tbl_task_assignees (task_id, user_id, deleted_on)
                VALUES (%s, %s, NULL)
                ON DUPLICATE KEY UPDATE
                    deleted_on = NULL,
                    updated_on = UTC_TIMESTAMP()
                """,
                (task_id, uid)
            )

    await cur.execute(
        """
        SELECT
            task_id, project_id, title, description, status, priority,
            is_responsible, due_date, completed_at, completed_by,
            parent_id, created_by, created_on, updated_on
        FROM tbl_tasks
        WHERE task_id = %s
        """,
        (task_id,)
    )
    row = await cur.fetchone()
    assignees = await _fetch_task_assignees(cur, task_id)
    return row, assignees



async def delete_task(cur, task_id: int):
    await cur.execute(
        "SELECT task_id FROM tbl_tasks WHERE task_id = %s AND deleted_on IS NULL",
        (task_id,)
    )
    if not await cur.fetchone():
        raise ValueError("Task not found")

    await cur.execute(
        "UPDATE tbl_tasks SET deleted_on = UTC_TIMESTAMP() WHERE task_id = %s",
        (task_id,)
    )
    await cur.execute(
        """
        UPDATE tbl_task_assignees
        SET deleted_on = UTC_TIMESTAMP()
        WHERE task_id = %s AND deleted_on IS NULL
        """,
        (task_id,)
    )
    
    
    
    

    