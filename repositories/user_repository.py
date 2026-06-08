from datetime import datetime, timedelta, timezone
import schemas.User_schemas as User_schemas
import utilities.security as security


async def get_user_by_email_hmac(cur, email: str):
    hmac_val = security.compute_hmac(email)
    await cur.execute(
        "SELECT * FROM tbl_users WHERE email_hmac = %s AND deleted_on IS NULL",
        (hmac_val,)
    )
    return await cur.fetchone()

async def get_user_by_username_hmac(cur, username: str):
    hmac_val = security.compute_hmac(username)
    await cur.execute(
        """
        SELECT *FROM tbl_users
        WHERE username_hmac = %s
        AND deleted_on IS NULL
        LIMIT 1
        """,
        (hmac_val,))
    return await cur.fetchone()

async def get_user_by_id(cur, user_id: int):
    await cur.execute(
        """
        SELECT * FROM tbl_users
        WHERE user_id = %s
        AND deleted_on IS NULL
        LIMIT 1
        """,
        (user_id,)
    )
    return await cur.fetchone()

async def create_user(cur, payload: User_schemas.SignupRequest) -> int:
    existing_email = await get_user_by_email_hmac(cur, payload.email)
    existing_username = await get_user_by_username_hmac(cur, payload.username)

    if existing_email:
        raise ValueError("Email already exists")
    if existing_username:
        raise ValueError("Username already exists")

    enc_email = security.encrypt_field(payload.email)
    enc_username = security.encrypt_field(payload.username)
    email_hmac = security.compute_hmac(payload.email)
    username_hmac = security.compute_hmac(payload.username)
    await cur.execute(
        """
        INSERT INTO tbl_users
        (full_name, username, username_hmac, email, email_hmac, status)
        VALUES (%s, %s, %s, %s, %s, %s)
        """,
        (
            payload.full_name,
            enc_username,
            username_hmac,
            enc_email,
            email_hmac,
            "Active"
        )
    )

    user_id = cur.lastrowid
    hashed_pw = security.hash_password(payload.password)

    await cur.execute(
        """
        INSERT INTO tbl_passwords
        (user_id, password, status, created_on)
        VALUES (%s, %s, %s, UTC_TIMESTAMP())
        """,
        (user_id, hashed_pw, 1)
    )

    role_id = payload.role_id if payload.role_id else 5
    await cur.execute(
        """
        SELECT role_id FROM tbl_roles 
        WHERE role_id = %s AND status = 1 AND deleted_on IS NULL
        LIMIT 1
        """,
        (role_id,)
    )
    valid_role = await cur.fetchone()

    if valid_role:
        await cur.execute(
            """
            INSERT INTO tbl_user_role
            (role_id, user_id, status, created_on, updated_on)
            VALUES (%s, %s, 'active', UTC_TIMESTAMP(), UTC_TIMESTAMP())
            """,
            (role_id, user_id)
        )

    return user_id

async def authenticate_user(cur,email: str,password: str):
    user = await get_user_by_email_hmac(cur,email)
    if not user:
        return None
    if user["status"] != "Active":
        raise PermissionError("Account unavailable")
    await cur.execute(
        """
        SELECT password FROM tbl_passwords
        WHERE user_id = %s
        AND deleted_on IS NULL
        AND status = 1
        ORDER BY created_on DESC
        LIMIT 1
        """,
        (user["user_id"],)
    )

    pw_record = await cur.fetchone()
    if not pw_record:
        return None

    if not security.verify_password(password,pw_record["password"]):
        return None
    return user


async def update_last_login(cur,user_id: int):
    await cur.execute(
        """
        UPDATE tbl_users
        SET last_login_at = UTC_TIMESTAMP()
        WHERE user_id = %s
        """,
        (user_id,)
    )


async def create_password_reset(cur, user_id: int, token_hash: str, expires_at: datetime):
    await cur.execute(
        """INSERT INTO tbl_reset_password 
           (user_id, reset_token_hash, expires_at) 
           VALUES (%s, %s, %s)""",
        (user_id, token_hash, expires_at)
    )


async def validate_reset_token(cur, raw_token: str):
    token_hash = security.hash_reset_token(raw_token)
    await cur.execute(
        """SELECT * FROM tbl_reset_password 
           WHERE reset_token_hash = %s 
             AND used_at IS NULL 
             AND expires_at > UTC_TIMESTAMP()""",
        (token_hash,)
    )
    return await cur.fetchone()

async def reset_user_password(cur, rp_id: int, user_id: int, new_password: str):
    hashed = security.hash_password(new_password)
    await cur.execute(
        "UPDATE tbl_passwords SET password = %s, updated_on = NOW() WHERE user_id = %s",
        (hashed, user_id)
    )
    await cur.execute(
        "UPDATE tbl_reset_password SET used_at = NOW() WHERE rp_id = %s",
        (rp_id,)
    )
    
async def create_refresh_token(cur,user_id: int) -> str:

    await cur.execute(
        """
        UPDATE tbl_refresh_tokens
        SET revoked_at = UTC_TIMESTAMP()
        WHERE user_id = %s
        AND revoked_at IS NULL
        """,
        (user_id,)
    )

    raw_token, token_hash = (
        security.generate_refresh_token()
    )

    expire = (datetime.now(timezone.utc) + timedelta(days=security.REFRESH_EXPIRE_DAYS))
    await cur.execute(
        """
        INSERT INTO tbl_refresh_tokens
        (user_id,token_hash,expires_at,created_at
        )
        VALUES
        (%s,%s,%s,UTC_TIMESTAMP())
        """,
        (user_id,token_hash,expire))

    return raw_token


async def validate_refresh_token(cur,raw_token: str):
    token_hash = security.hash_refresh_token(raw_token)
    await cur.execute(
        """
        SELECT * FROM tbl_refresh_tokens
        WHERE token_hash = %s
        AND revoked_at IS NULL
        AND expires_at > UTC_TIMESTAMP()
        LIMIT 1
        """,
        (token_hash,)
    )
    return await cur.fetchone()


async def revoke_refresh_token(cur,token_id: int):
    await cur.execute(
        """
        UPDATE tbl_refresh_tokens
        SET revoked_at = UTC_TIMESTAMP()
        WHERE rt_id = %s
        """,
        (token_id,)
    )
    
async def get_user_roles(cur, user_id: int):
    await cur.execute(
        """
        SELECT 
            r.role_id,
            r.role_name,
            r.role_slug,
            r.description
        FROM tbl_user_role ur
        JOIN tbl_roles r ON ur.role_id = r.role_id
        WHERE ur.user_id = %s
          AND ur.status = 'active'
          AND r.status = 1
          AND r.deleted_on IS NULL
          AND ur.deleted_on IS NULL
        """,
        (user_id,)
    )
    return await cur.fetchall()


async def get_user_permissions(cur, user_id: int):
    await cur.execute(
        """
        SELECT 
            mrp.permission_id,
            mrp.module_id,
            m.module_name,
            mrp.permission_name,
            mrp.permission_slug,
            mrp.resource,
            mrp.action,
            mrp.description
        FROM tbl_module_role_permissions mrp
        JOIN tbl_modules m ON mrp.module_id = m.module_id
        WHERE mrp.role_id IN (
            SELECT role_id 
            FROM tbl_user_role 
            WHERE user_id = %s 
              AND status = 'active' 
              AND deleted_on IS NULL
        )
          AND mrp.status = 1
          AND mrp.deleted_on IS NULL
          AND m.status = 1
        """,
        (user_id,)
    )
    return await cur.fetchall()





    
    