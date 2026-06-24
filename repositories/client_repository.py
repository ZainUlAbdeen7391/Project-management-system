from utilities.uuid_utils import generate_uuid7

# create client
async def create_client(cur, payload, user_id: str):
    await cur.execute(
        """
        SELECT client_id FROM tbl_client
        WHERE LOWER(client_name) = LOWER(%s)
        AND deleted_on IS NULL
        LIMIT 1
        """,
        (payload.client_name,),
    )
    if await cur.fetchone():
        raise ValueError("Client already exists")

    client_id = generate_uuid7()
    await cur.execute(
        """
        INSERT INTO tbl_client (client_id, client_name, client_type, status, created_by, updated_by)
        VALUES (%s, %s, %s, 1, %s, %s)
        """,
        (client_id, payload.client_name, payload.client_type.value, user_id, user_id),
    )

    for loc in payload.locations:
        await cur.execute(
            """
            SELECT poc_id FROM tbl_client_poc
            WHERE email = %s AND deleted_on IS NULL
            LIMIT 1
            """,
            (loc.poc.email,),
        )
        if await cur.fetchone():
            raise ValueError(f"POC email '{loc.poc.email}' already exists")

        await cur.execute(
            """
            SELECT poc_id FROM tbl_client_poc
            WHERE phone = %s AND deleted_on IS NULL
            LIMIT 1
            """,
            (loc.poc.phone,),
        )
        if await cur.fetchone():
            raise ValueError(f"POC phone '{loc.poc.phone}' already exists")

        address_id = generate_uuid7()
        await cur.execute(
            """
            INSERT INTO tbl_client_address
            (address_id, client_id, address_line_1, address_line_2, city, state,
            zip_code, country, address_type, is_primary, status)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 1)
            """,
            (
                address_id,
                client_id,
                loc.address.address_line_1,
                loc.address.address_line_2,
                loc.address.city,
                loc.address.state,
                loc.address.zip_code,
                loc.address.country or "Pakistan",
                loc.address.address_type.value if loc.address.address_type else "Office",
                1 if loc.address.is_primary else 0,
            ),
        )

        poc_id = generate_uuid7()
        await cur.execute(
            """
            INSERT INTO tbl_client_poc
            (poc_id, client_id, address_id, full_name, email, phone, status)
            VALUES (%s, %s, %s, %s, %s, %s, 1)
            """,
            (
                poc_id,
                client_id,
                address_id,
                loc.poc.full_name,
                loc.poc.email,
                loc.poc.phone,
            ),
        )

    return await fetch_client_detail(cur, client_id)


async def fetch_client_detail(cur, client_id: str):
    await cur.execute(
        """
        SELECT client_id, client_name, client_type, status,
        created_by, updated_by, created_on, updated_on
        FROM tbl_client
        WHERE client_id = %s AND deleted_on IS NULL
        """,
        (client_id,),
    )
    client = await cur.fetchone()
    if not client:
        raise ValueError("Client not found")
    await cur.execute(
        """
        SELECT address_id, client_id, address_line_1, address_line_2,
        city, state, zip_code, country, address_type, is_primary,
        status, created_on, updated_on
        FROM tbl_client_address
        WHERE client_id = %s AND deleted_on IS NULL
        ORDER BY is_primary DESC, address_id ASC
        """,
        (client_id,),
    )
    addresses = await cur.fetchall()
    await cur.execute(
        """
        SELECT poc_id, client_id, address_id, full_name, email, phone,
        status, created_on, updated_on
        FROM tbl_client_poc
        WHERE client_id = %s AND deleted_on IS NULL
        ORDER BY poc_id ASC
        """,
        (client_id,),
    )
    pocs = await cur.fetchall()
    return {"client": client, "addresses": addresses, "pocs": pocs}


# get all clients
async def list_clients(cur):
    await cur.execute(
        """
        SELECT client_id, client_name, client_type, status,
               created_by, updated_by, created_on, updated_on
        FROM tbl_client
        WHERE deleted_on IS NULL
        ORDER BY client_id DESC
        """
    )
    clients = await cur.fetchall()

    result = []
    for client in clients:
        client_id = client["client_id"]

        await cur.execute(
            """
            SELECT address_id, client_id, address_line_1, address_line_2,
                   city, state, zip_code, country, address_type,
                   is_primary, status, created_on, updated_on
            FROM tbl_client_address
            WHERE client_id = %s
              AND deleted_on IS NULL
            ORDER BY is_primary DESC, address_id ASC
            """,
            (client_id,),
        )
        addresses = await cur.fetchall()

        await cur.execute(
            """
            SELECT poc_id, client_id, address_id, full_name,
                   email, phone, status, created_on, updated_on
            FROM tbl_client_poc
            WHERE client_id = %s
              AND deleted_on IS NULL
            ORDER BY poc_id ASC
            """,
            (client_id,),
        )
        pocs = await cur.fetchall()

        client["addresses"] = addresses
        client["pocs"] = pocs

        result.append(client)

    return result


# get Single Client
async def get_client(cur, client_id: str):
    return await fetch_client_detail(cur, client_id)


# update client
async def update_client(cur, client_id: str, payload, user_id: str):
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
            (payload.client_name, client_id),
        )
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
    values.append(client_id)

    await cur.execute(
        f"""
        UPDATE tbl_client
        SET {', '.join(fields)}
        WHERE client_id = %s AND deleted_on IS NULL
        """,
        tuple(values),
    )
    return await fetch_client_detail(cur, client_id)


# update client address
async def update_address(cur, client_id: str, address_id: str, payload, user_id: str):
    # verify address belongs to the client
    await cur.execute(
        """
        SELECT address_id FROM tbl_client_address
        WHERE client_id = %s AND address_id = %s AND deleted_on IS NULL
        """, 
        (client_id, address_id)
    )
    if not await cur.fetchone():
        raise ValueError("Address not found")

    fields = []
    values = []
    if payload.address_line_1 is not None:
        fields.append("address_line_1 = %s")
        values.append(payload.address_line_1)
    if payload.address_line_2 is not None:
        fields.append("address_line_2 = %s")
        values.append(payload.address_line_2)
    if payload.city is not None:
        fields.append("city = %s")
        values.append(payload.city)
    if payload.state is not None:
        fields.append("state = %s")
        values.append(payload.state)
    if payload.zip_code is not None:
        fields.append("zip_code = %s")
        values.append(payload.zip_code)
    if payload.country is not None:
        fields.append("country = %s")
        values.append(payload.country)
    if payload.address_type is not None:
        fields.append("address_type = %s")
        values.append(payload.address_type.value)
    if payload.is_primary is not None:
        fields.append("is_primary = %s")
        values.append(1 if payload.is_primary else 0)
    if payload.status is not None:
        fields.append("status = %s")
        values.append(1 if payload.status else 0)

    if not fields:
        raise ValueError("No fields to update")

    fields.append("updated_on = NOW()")
    values.append(address_id)

    await cur.execute(
        f"""
        UPDATE tbl_client_address 
        SET {', '.join(fields)} 
        WHERE address_id = %s
        """,
        tuple(values)
    )
    return {"address_id": address_id}


# update POC
async def update_poc(cur, client_id: str, poc_id: str, payload, user_id: str):
    # verify POC belongs to client
    await cur.execute(
        """
        SELECT poc_id, email, phone FROM tbl_client_poc
        WHERE poc_id = %s AND client_id = %s AND deleted_on IS NULL
        """,
        (poc_id, client_id)
    )
    existing = await cur.fetchone()
    if not existing:
        raise ValueError("POC not found")

    fields = []
    values = []
    if payload.full_name is not None:
        fields.append("full_name = %s")
        values.append(payload.full_name)
    if payload.email is not None and payload.email != existing["email"]:
        await cur.execute(
            """
            SELECT poc_id FROM tbl_client_poc 
            WHERE email = %s AND deleted_on IS NULL AND poc_id != %s
            """,
            (payload.email, poc_id)
        )
        if await cur.fetchone():
            raise ValueError(f"POC email '{payload.email}' already exists")
        fields.append("email = %s")
        values.append(payload.email)
    if payload.phone is not None and payload.phone != existing["phone"]:
        await cur.execute(
            """
            SELECT poc_id FROM tbl_client_poc 
            WHERE phone = %s AND deleted_on IS NULL AND poc_id != %s
            """,
            (payload.phone, poc_id)
        )
        if await cur.fetchone():
            raise ValueError(f"POC phone '{payload.phone}' already exists")
        fields.append("phone = %s")
        values.append(payload.phone)

    if payload.address_id is not None:
        # verify new address belongs to same client
        await cur.execute(
            """
            SELECT address_id FROM tbl_client_address 
            WHERE address_id = %s AND client_id = %s AND deleted_on IS NULL
            """,
            (payload.address_id, client_id)
        )
        if not await cur.fetchone():
            raise ValueError("Address not found for this client")
        fields.append("address_id = %s")
        values.append(payload.address_id)
    if payload.status is not None:
        fields.append("status = %s")
        values.append(1 if payload.status else 0)

    if not fields:
        raise ValueError("No fields to update")

    fields.append("updated_on = NOW()")
    values.append(poc_id)

    await cur.execute(
        f"""
        UPDATE tbl_client_poc 
        SET {', '.join(fields)} 
        WHERE poc_id = %s
        """,
        tuple(values)
    )
    return {"poc_id": poc_id}


# delete client / address / poc
async def delete_client_entity(cur, entity_type: str, entity_id: str, user_id: str):
    if entity_type == "client":
        await cur.execute(
            """
            SELECT client_id
            FROM tbl_client
            WHERE client_id = %s
            AND deleted_on IS NULL
            """,
            (entity_id,),
        )
        if not await cur.fetchone():
            raise ValueError("Client not found")

        await cur.execute(
            """
            UPDATE tbl_client
            SET deleted_on = NOW(), updated_on = NOW(),
            updated_by = %s, status = 0
            WHERE client_id = %s
            """,
            (user_id, entity_id),
        )
        return {"message": "Client deleted successfully"}

    elif entity_type == "address":
        await cur.execute(
            """
            SELECT address_id
            FROM tbl_client_address
            WHERE address_id = %s
            AND deleted_on IS NULL
            """,
            (entity_id,),
        )
        if not await cur.fetchone():
            raise ValueError("Address not found")

        await cur.execute(
            """
            UPDATE tbl_client_address
            SET deleted_on = NOW(), updated_on = NOW(), status = 0
            WHERE address_id = %s
            """,
            (entity_id,),
        )
        return {"message": "Address deleted successfully"}

    elif entity_type == "poc":
        await cur.execute(
            """
            SELECT poc_id
            FROM tbl_client_poc
            WHERE poc_id = %s AND deleted_on IS NULL
            """,
            (entity_id,),
        )
        if not await cur.fetchone():
            raise ValueError("POC not found")

        await cur.execute(
            """
            UPDATE tbl_client_poc
            SET deleted_on = NOW(), updated_on = NOW(), status = 0
            WHERE poc_id = %s
            """,
            (entity_id,),
        )
        return {"message": "POC deleted successfully"}

    else:
        raise ValueError("Invalid entity type")