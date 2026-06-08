async def _check_task_access(cur, task_id: int, user_id: int):
    # check is_responsible
    await cur.execute(
        """
        SELECT task_id FROM tbl_tasks
        WHERE task_id = %s AND is_responsible = %s AND deleted_on IS NULL
        """,
        (task_id, user_id)
    )
    if await cur.fetchone():
        return

    #check assignee
    await cur.execute(
        """
        SELECT id FROM tbl_task_assignees
        WHERE task_id = %s AND user_id = %s AND deleted_on IS NULL
        """,
        (task_id, user_id)
    )
    if await cur.fetchone():
        return

    #check project member
    await cur.execute(
        """
        SELECT pm.member_id FROM tbl_project_members pm
        INNER JOIN tbl_tasks t ON t.project_id = pm.project_id
        WHERE t.task_id = %s
        AND pm.user_id = %s
        AND t.deleted_on IS NULL
        AND pm.deleted_on IS NULL
        """,
        (task_id, user_id)
    )
    if await cur.fetchone():
        return

    raise ValueError("You are not authorized to comment on this task")


async def _check_comment_owner(cur, comment_id: int, user_id: int):
    await cur.execute(
        """
        SELECT comment_id FROM tbl_comments
        WHERE comment_id = %s AND created_by = %s AND deleted_on IS NULL
        """,
        (comment_id, user_id)
    )
    if not await cur.fetchone():
        raise ValueError("You can only delete or edit your own comment")


async def _fetch_replies(cur, parent_id: int) -> list[dict]:
    await cur.execute(
        """
        SELECT
            c.comment_id, c.task_id, c.parent_id, c.comment,
            c.created_by AS user_id, u.full_name,
            c.created_on, c.updated_on
        FROM tbl_comments c
        LEFT JOIN tbl_users u ON c.created_by = u.user_id
        WHERE c.parent_id = %s AND c.deleted_on IS NULL
        ORDER BY c.created_on ASC
        """,
        (parent_id,)
    )
    replies = await cur.fetchall()
    result = []
    for reply in replies:
        nested = await _fetch_replies(cur, reply["comment_id"])
        result.append({**reply, "replies": nested})
    return result



async def create_comment(cur, task_id: int, comment: str, parent_id: int | None, user_id: int):
    await cur.execute(
        "SELECT task_id FROM tbl_tasks WHERE task_id = %s AND deleted_on IS NULL",
        (task_id,)
    )
    if not await cur.fetchone():
        raise ValueError("Task does not exist")

    await _check_task_access(cur, task_id, user_id)

    if parent_id is not None and parent_id != 0:
        await cur.execute(
            """
            SELECT comment_id FROM tbl_comments
            WHERE comment_id = %s AND task_id = %s AND deleted_on IS NULL
            """,
            (parent_id, task_id)
        )
        if not await cur.fetchone():
            raise ValueError("Parent comment does not exist on this task")
    else:
        parent_id = None

    await cur.execute(
        """
        INSERT INTO tbl_comments
            (task_id, user_id, parent_id, comment, status, created_by, updated_by)
        VALUES (%s, %s, %s, %s, 1, %s, %s)
        """,
        (task_id, user_id, parent_id, comment, user_id, user_id)
    )

    comment_id = getattr(cur, "lastrowid", None)
    if not comment_id:
        await cur.execute("SELECT LAST_INSERT_ID() as id")
        result = await cur.fetchone()
        comment_id = result["id"] if result else None

    if not comment_id:
        raise RuntimeError("Failed to retrieve comment_id after insert")

    await cur.execute(
        """
        SELECT
            c.comment_id, c.task_id, c.parent_id, c.comment,
            c.created_by AS user_id, u.full_name,
            c.created_on, c.updated_on
        FROM tbl_comments c
        LEFT JOIN tbl_users u ON c.created_by = u.user_id
        WHERE c.comment_id = %s
        """,
        (comment_id,)
    )
    return await cur.fetchone()



async def list_comments(cur, task_id: int, user_id: int):
    await cur.execute(
        "SELECT task_id FROM tbl_tasks WHERE task_id = %s AND deleted_on IS NULL",
        (task_id,)
    )
    if not await cur.fetchone():
        raise ValueError("Task does not exist")

    await _check_task_access(cur, task_id, user_id)

    await cur.execute(
        """
        SELECT
            c.comment_id, c.task_id, c.parent_id, c.comment,
            c.created_by AS user_id, u.full_name,
            c.created_on, c.updated_on
        FROM tbl_comments c
        LEFT JOIN tbl_users u ON c.created_by = u.user_id
        WHERE c.task_id = %s AND c.parent_id IS NULL AND c.deleted_on IS NULL
        ORDER BY c.created_on ASC
        """,
        (task_id,)
    )
    top_level = await cur.fetchall()

    result = []
    for comment in top_level:
        replies = await _fetch_replies(cur, comment["comment_id"])
        result.append({**comment, "replies": replies})
    return result



async def update_comment(cur, comment_id: int, new_comment: str, user_id: int):
    await cur.execute(
        """
        SELECT comment_id FROM tbl_comments
        WHERE comment_id = %s AND deleted_on IS NULL
        """,
        (comment_id,)
    )
    if not await cur.fetchone():
        raise ValueError("Comment does not exist")

    await _check_comment_owner(cur, comment_id, user_id)

    await cur.execute(
        """
        UPDATE tbl_comments
        SET comment = %s, updated_by = %s
        WHERE comment_id = %s AND deleted_on IS NULL
        """,
        (new_comment, user_id, comment_id)
    )

    await cur.execute(
        """
        SELECT
            c.comment_id, c.task_id, c.parent_id, c.comment,
            c.created_by AS user_id, u.full_name,
            c.created_on, c.updated_on
        FROM tbl_comments c
        LEFT JOIN tbl_users u ON c.created_by = u.user_id
        WHERE c.comment_id = %s
        """,
        (comment_id,)
    )
    return await cur.fetchone()


async def delete_comment(cur, comment_id: int, user_id: int):
    await cur.execute(
        """
        SELECT comment_id FROM tbl_comments
        WHERE comment_id = %s AND deleted_on IS NULL
        """,
        (comment_id,)
    )
    if not await cur.fetchone():
        raise ValueError("Comment does not exist")

    await _check_comment_owner(cur, comment_id, user_id)

    # ✅ soft delete the comment itself first
    await cur.execute(
        """
        UPDATE tbl_comments
        SET deleted_on = UTC_TIMESTAMP()
        WHERE comment_id = %s AND deleted_on IS NULL
        """,
        (comment_id,)
    )
 
    await cur.execute(
        """
        UPDATE tbl_comments
        SET deleted_on = UTC_TIMESTAMP()
        WHERE parent_id = %s AND deleted_on IS NULL
        """,
        (comment_id,)
    )


    
    
    
    
    
    