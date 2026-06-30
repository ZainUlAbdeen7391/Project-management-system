from datetime import datetime, timedelta, timezone
import schemas.User_schemas as User_schemas
import utilities.security as security
from utilities.uuid_utils import generate_uuid7

async def get_user_by_email(cur, email: str):
    enc_email = security.encrypt_for_search(email)
    await cur.execute(
        "SELECT * FROM tbl_users WHERE email = %s AND deleted_on IS NULL",
        (enc_email,),
    )
    return await cur.fetchone()


async def get_user_by_username(cur, username: str):
    enc_username = security.encrypt_for_search(username)
    await cur.execute(
        """
        SELECT * FROM tbl_users
        WHERE username = %s
          AND deleted_on IS NULL
        LIMIT 1
        """,
        (enc_username,),
    )
    return await cur.fetchone()


async def get_user_by_id(cur, user_id: str):
    await cur.execute(
        """
        SELECT * FROM tbl_users
        WHERE user_id = %s
          AND deleted_on IS NULL
        LIMIT 1
        """,
        (user_id,),
    )
    return await cur.fetchone()


async def get_phone_by_user_id(cur, user_id: str):
    """Returns the primary active phone row for a user."""
    await cur.execute(
        """
        SELECT id, user_id, phone_number, phone_type, is_primary, status
        FROM tbl_phones
        WHERE user_id = %s
          AND is_primary = 1
          AND deleted_on IS NULL
        LIMIT 1
        """,
        (user_id,),
    )
    return await cur.fetchone()


#create User

async def create_user(cur, payload: User_schemas.SignupRequest) -> str:
    #Duplicate checks
    existing_email    = await get_user_by_email(cur, payload.email)
    existing_username = await get_user_by_username(cur, payload.username)

    if existing_email:
        raise ValueError("Email already exists")
    if existing_username:
        raise ValueError("Username already exists")

#Phone duplicate check
    enc_phone_check = security.encrypt_for_search(payload.phone_number)
    await cur.execute(
        """
        SELECT id FROM tbl_phones
        WHERE phone_number = %s
          AND deleted_on IS NULL
        LIMIT 1
        """,
        (enc_phone_check,),
    )
    if await cur.fetchone():
        raise ValueError("Phone number already exists")

#Encrypt fields for storage
    user_id      = generate_uuid7()
    enc_email    = security.encrypt_field(payload.email)
    enc_username = security.encrypt_field(payload.username)

    await cur.execute(
        """
        INSERT INTO tbl_users
            (user_id, full_name, username, email, status)
        VALUES (%s, %s, %s, %s, %s)
        """,
        (user_id, payload.full_name, enc_username, enc_email, "Active"),
    )

    #Password
    password_id = generate_uuid7()
    hashed_pw   = security.hash_password(payload.password)
    await cur.execute(
        """
        INSERT INTO tbl_passwords (id, user_id, password, status, created_on)
        VALUES (%s, %s, %s, 1, UTC_TIMESTAMP())
        """,
        (password_id, user_id, hashed_pw),
    )

#phone
    phone_id  = generate_uuid7()
    enc_phone = security.encrypt_field(payload.phone_number)
    await cur.execute(
        """
        INSERT INTO tbl_phones
            (id, user_id, phone_number, phone_type, is_primary, status,
             created_by, updated_by)
        VALUES (%s, %s, %s, 'Personal', 1, 1, %s, %s)
        """,
        (phone_id, user_id, enc_phone, user_id, user_id),
    )

    #Role assignment
    role_id = payload.role_id if payload.role_id else 5
    await cur.execute(
        """
        SELECT role_id FROM tbl_roles
        WHERE role_id = %s AND status = 1 AND deleted_on IS NULL
        LIMIT 1
        """,
        (role_id,),
    )
    valid_role = await cur.fetchone()
    if valid_role:
        ur_id = generate_uuid7()
        await cur.execute(
            """
            INSERT INTO tbl_user_role
                (ur_id, role_id, user_id, status, created_on, updated_on)
            VALUES (%s, %s, %s, 'active', UTC_TIMESTAMP(), UTC_TIMESTAMP())
            """,
            (ur_id, role_id, user_id),
        )
    return user_id
#Authenticate

async def authenticate_user(cur, email: str, password: str):
    user = await get_user_by_email(cur, email)
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
        (user["user_id"],),
    )
    pw_record = await cur.fetchone()
    if not pw_record:
        return None
    if not security.verify_password(password, pw_record["password"]):
        return None
    return user


#last login

async def update_last_login(cur, user_id: str):
    await cur.execute(
        "UPDATE tbl_users SET last_login_at = UTC_TIMESTAMP() WHERE user_id = %s",
        (user_id,),
    )


#Password reset

async def create_password_reset(cur, user_id: str, token_hash: str, expires_at: datetime):
    rp_id = generate_uuid7()
    await cur.execute(
        """
        INSERT INTO tbl_reset_password (rp_id, user_id, reset_token_hash, expires_at)
        VALUES (%s, %s, %s, %s)
        """,
        (rp_id, user_id, token_hash, expires_at),
    )


async def validate_reset_token(cur, raw_token: str):
    token_hash = security.hash_reset_token(raw_token)
    await cur.execute(
        """
        SELECT * FROM tbl_reset_password
        WHERE reset_token_hash = %s
          AND used_at IS NULL
          AND expires_at > UTC_TIMESTAMP()
        """,
        (token_hash,),
    )
    return await cur.fetchone()


async def reset_user_password(cur, rp_id: str, user_id: str, new_password: str):
    hashed = security.hash_password(new_password)
    await cur.execute(
        "UPDATE tbl_passwords SET password = %s, updated_on = NOW() WHERE user_id = %s",
        (hashed, user_id),
    )
    await cur.execute(
        "UPDATE tbl_reset_password SET used_at = NOW() WHERE rp_id = %s",
        (rp_id,),
    )


#refresh tokens

async def create_refresh_token(cur, user_id: str) -> str:
    await cur.execute(
        """
        UPDATE tbl_refresh_tokens
        SET revoked_at = UTC_TIMESTAMP()
        WHERE user_id = %s AND revoked_at IS NULL
        """,
        (user_id,),
    )
    raw_token, token_hash = security.generate_refresh_token()
    expire = datetime.now(timezone.utc) + timedelta(days=security.REFRESH_EXPIRE_DAYS)
    rt_id  = generate_uuid7()
    await cur.execute(
        """
        INSERT INTO tbl_refresh_tokens (rt_id, user_id, token_hash, expires_at, created_at)
        VALUES (%s, %s, %s, %s, UTC_TIMESTAMP())
        """,
        (rt_id, user_id, token_hash, expire),
    )
    return raw_token


async def validate_refresh_token(cur, raw_token: str):
    token_hash = security.hash_refresh_token(raw_token)
    await cur.execute(
        """
        SELECT * FROM tbl_refresh_tokens
        WHERE token_hash = %s
          AND revoked_at IS NULL
          AND expires_at > UTC_TIMESTAMP()
        LIMIT 1
        """,
        (token_hash,),
    )
    return await cur.fetchone()


async def revoke_refresh_token(cur, token_id: str):
    await cur.execute(
        "UPDATE tbl_refresh_tokens SET revoked_at = UTC_TIMESTAMP() WHERE rt_id = %s",
        (token_id,),
    )


#Roles & Permissions
async def get_user_roles(cur, user_id: str):
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
        (user_id,),
    )
    return await cur.fetchall()


async def get_user_permissions(cur, user_id: str):
    await cur.execute(
        """
        SELECT DISTINCT
            p.permission_id,
            p.role_id,
            p.module_id,
            m.module_name,
            m.module_slug,
            p.permission_name,
            p.permission_slug,
            p.resource,
            p.action,
            p.description
        FROM tbl_user_role ur
        INNER JOIN tbl_roles r
            ON ur.role_id = r.role_id
            AND r.deleted_on IS NULL
            AND r.status = 1
        INNER JOIN tbl_module_role_permissions p
            ON r.role_id = p.role_id
            AND p.deleted_on IS NULL
            AND p.status = 1
        INNER JOIN tbl_modules m
            ON p.module_id = m.module_id
            AND m.deleted_on IS NULL
            AND m.status = 1
        WHERE ur.user_id = %s
          AND ur.status = 'active'
          AND ur.deleted_on IS NULL
        ORDER BY m.module_name, p.resource, p.action
        """,
        (user_id,),
    )
    return await cur.fetchall()