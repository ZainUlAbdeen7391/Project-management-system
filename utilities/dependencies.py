from fastapi import Depends, HTTPException, status
import json
from fastapi.security import OAuth2PasswordBearer
from repositories import user_repository
from configurations.database import get_db
import aiomysql
from utilities import security


oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


async def get_current_user(token: str = Depends(oauth2_scheme),cur: aiomysql.DictCursor = Depends(get_db)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        payload = security.decode_access_token(token)
    except Exception:
        raise credentials_exception

    if payload is None:
        raise credentials_exception

    user_id = payload.get("sub")
    if user_id is None:
        raise credentials_exception

    user = await user_repository.get_user_by_id(cur, int(user_id))

    if user is None:
        raise credentials_exception

    status_val = user["status"]
    if isinstance(status_val, bytes):
        status_val = status_val.decode("utf-8")

    if status_val.lower() != "active":
        raise credentials_exception


    if user.get("deleted_on") is not None:
        raise credentials_exception

    return user


# Requires Permissions
def require_permission(module_slug: str, resource: str, action: str):
    async def _checker(current_user: dict = Depends(get_current_user),cur=Depends(get_db)):
        await cur.execute("""
            SELECT p.permission_id 
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
            WHERE ur.user_id = %s 
              AND ur.status = 'active' 
              AND ur.deleted_on IS NULL
              AND m.module_slug = %s
              AND p.resource = %s
              AND p.action = %s
            LIMIT 1
        """, (
            current_user["user_id"],
            module_slug,
            resource,
            action
        ))

        row = await cur.fetchone()
        if not row:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Permission denied: '{action}' on '{resource}' in '{module_slug}'."
            )
        return current_user
    return _checker

#Activity Log
async def log_activity(
    cur: aiomysql.DictCursor,
    user_id: int,
    action: str,
    entity_type: str,
    entity_id: int = None,
    description: str = None,
    old_values: dict = None,
    new_values: dict = None
):
    await cur.execute("""
        INSERT INTO tbl_activity_logs 
        (user_id, action, entity_type, entity_id, description, old_values, new_values, created_on)
        VALUES (%s, %s, %s, %s, %s, %s, %s, NOW())
    """, (
        user_id,
        action,
        entity_type,
        entity_id,
        description,
        json.dumps(old_values) if old_values else None,
        json.dumps(new_values) if new_values else None
    ))
    
    
    
    














        
    


