async def create_client(cur, payload, user_id: int):
    await cur.execute(
        """
        SELECT client_id
        FROM tbl_client
        WHERE LOWER(client_name) = LOWER(%s)
        AND deleted_on IS NULL
        LIMIT 1
        """,(payload.client_name,),)
    if await cur.fetchone():
        raise ValueError("Client already exists")

    await cur.execute(
        """
        INSERT INTO tbl_client
        (client_name, client_type, status, created_by, updated_by)
        VALUES (%s, %s, %s, %s, %s)
        """,
        (
            payload.client_name,
            payload.client_type.value,
            1,
            user_id,
            user_id,
        ),)

    client_id = getattr(cur, "lastrowid", None)
    if not client_id:
        await cur.execute("SELECT LAST_INSERT_ID() AS id")
        result = await cur.fetchone()
        client_id = result["id"]

    await cur.execute(
        """
        SELECT poc_id FROM tbl_client_poc
        WHERE email = %s AND deleted_on IS NULL
        LIMIT 1
        """,
        (payload.poc.email,),)
    if await cur.fetchone():
        raise ValueError("POC email already exists")
    await cur.execute(
        """
        SELECT poc_id FROM tbl_client_poc
        WHERE phone = %s AND deleted_on IS NULL
        LIMIT 1
        """,
        (payload.poc.phone,),)
    if await cur.fetchone():
        raise ValueError("POC phone already exists")

    await cur.execute(
        """
        INSERT INTO tbl_client_poc
        (client_id, full_name, email, phone, status)
        VALUES (%s, %s, %s, %s, %s)
        """,
        (
            client_id,
            payload.poc.full_name,
            payload.poc.email,
            payload.poc.phone,
            1,),)

    poc_id = getattr(cur, "lastrowid", None)
    if not poc_id:
        await cur.execute("SELECT LAST_INSERT_ID() AS id")
        result = await cur.fetchone()
        poc_id = result["id"]


    city = payload.address.city if payload.address.city else None
    state = payload.address.state if payload.address.state else None
    zip_code = payload.address.zip_code if payload.address.zip_code else None

    await cur.execute(
        """
        INSERT INTO tbl_client_address
        (poc_id, address_line_1, address_line_2, city, state, zip_code, country, address_type, is_primary, status)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """,
        (
            poc_id,
            payload.address.address_line_1,
            payload.address.address_line_2,
            city,
            state,
            zip_code,
            payload.address.country or "Pakistan",
            payload.address.address_type.value if payload.address.address_type else "Office",
            1 if payload.address.is_primary else 0,
            1,),)
    return await fetch_client_detail(cur, client_id)


async def fetch_client_detail(cur, client_id: int):
    await cur.execute(
        """
        SELECT client_id, client_name, client_type, status, created_by, updated_by, created_on, updated_on
        FROM tbl_client
        WHERE client_id = %s
        AND deleted_on IS NULL
        """,
        (client_id,),
    )
    client = await cur.fetchone()
    if not client:
        raise ValueError("Client not found")

    await cur.execute(
        """
        SELECT poc_id, client_id, full_name, email, phone, status, created_on, updated_on
        FROM tbl_client_poc
        WHERE client_id = %s
        AND deleted_on IS NULL
        ORDER BY poc_id ASC
        """,
        (client_id,),
    )
    pocs = await cur.fetchall()

    poc_ids = [p["poc_id"] for p in pocs]
    addresses = []
    if poc_ids:
        format_ids = ",".join(["%s"] * len(poc_ids))
        await cur.execute(
            f"""
            SELECT address_id, poc_id, address_line_1, address_line_2, city, state, zip_code, country,
                   address_type, is_primary, status, created_on, updated_on
            FROM tbl_client_address
            WHERE poc_id IN ({format_ids})
            AND deleted_on IS NULL
            ORDER BY is_primary DESC, address_id ASC
            """,
            tuple(poc_ids),)
        addresses = await cur.fetchall()

    return {
        "client": client,
        "addresses": addresses,
        "pocs": pocs,
    }


# ── List all clients ──
async def list_clients(cur):
    await cur.execute(
        """
        SELECT client_id, client_name, client_type, status, created_by, updated_by, created_on, updated_on
        FROM tbl_client
        WHERE deleted_on IS NULL
        ORDER BY client_id DESC
        """
    )
    return await cur.fetchall()


async def get_client(cur, client_id: int):
    return await fetch_client_detail(cur, client_id)


async def update_client(cur, client_id: int, payload, user_id: int):
    await cur.execute(
        """
        SELECT client_id FROM tbl_client
        WHERE client_id = %s AND deleted_on IS NULL
        """,
        (client_id,),
    )
    if not await cur.fetchone():
        raise ValueError("Client not found")

    if payload.client_name is not None:
        await cur.execute(
            """
            SELECT client_id FROM tbl_client
            WHERE LOWER(client_name) = LOWER(%s)
            AND deleted_on IS NULL
            AND client_id != %s
            LIMIT 1
            """,
            (payload.client_name, client_id),)
        if await cur.fetchone():
            raise ValueError("Client name already exists")

    fields = []
    values = []

    if payload.client_name is not None:
        fields.append("client_name = %s")
        values.append(payload.client_name)
    if payload.client_type is not None:
        fields.append("client_type = %s")
        values.append(payload.client_type.value)
    if payload.status is not None:
        fields.append("status = %s")
        values.append(1 if payload.status else 0)

    if not fields:
        raise ValueError("No fields to update")

    fields.append("updated_by = %s")
    values.append(user_id)
    fields.append("updated_on = NOW()")

    # WHERE clause parameter
    values.append(client_id)

    query = f"""
        UPDATE tbl_client
        SET {', '.join(fields)}
        WHERE client_id = %s
        AND deleted_on IS NULL
    """

    await cur.execute(query, tuple(values))
    await cur.execute(
        """
        SELECT client_id, client_name, client_type, status, created_by, updated_by, created_on, updated_on
        FROM tbl_client
        WHERE client_id = %s
        """,(client_id,),)
    return await cur.fetchone()


async def delete_client(cur, client_id: int, user_id: int):
    await cur.execute(
        """
        SELECT client_id FROM tbl_client
        WHERE client_id = %s AND deleted_on IS NULL
        """,
        (client_id,),)
    if not await cur.fetchone():
        raise ValueError("Client not found")

    await cur.execute(
        """
        SELECT poc_id FROM tbl_client_poc
        WHERE client_id = %s AND deleted_on IS NULL
        """,
        (client_id,),)
    poc_rows = await cur.fetchall()
    poc_ids = [r["poc_id"] for r in poc_rows]

    if poc_ids:
        format_ids = ",".join(["%s"] * len(poc_ids))
        await cur.execute(
            f"""
            UPDATE tbl_client_address
            SET deleted_on = NOW(), updated_on = NOW()
            WHERE poc_id IN ({format_ids})
            """,
            tuple(poc_ids),
        )
    await cur.execute(
        """
        UPDATE tbl_client_poc
        SET deleted_on = NOW(), updated_on = NOW()
        WHERE client_id = %s
        """,
        (client_id,),
    )
    await cur.execute(
        """
        UPDATE tbl_client
        SET deleted_on = NOW(), updated_on = NOW(), updated_by = %s
        WHERE client_id = %s
        """,
        (user_id, client_id),)
    return {"client_id": client_id}