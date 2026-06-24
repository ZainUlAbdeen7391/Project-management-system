from datetime import datetime, timedelta, UTC

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from fastapi_mail import FastMail, MessageSchema

import schemas.User_schemas as User_schemas
from configurations.database import get_db
from configurations.mail_config import MAIL_ENABLED, mail_conf
from repositories import user_repository
from utilities import security

router = APIRouter(prefix="/auth", tags=["Authentication"])


#Signup
@router.post("/signup", response_model=User_schemas.UserResponse, status_code=status.HTTP_201_CREATED)
async def signup(payload: User_schemas.SignupRequest, cur=Depends(get_db)):
    try:
        user_id = await user_repository.create_user(cur, payload)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

    user  = await user_repository.get_user_by_id(cur, user_id)
    phone = await user_repository.get_phone_by_user_id(cur, user_id)

    return User_schemas.UserResponse(
        user_id=user["user_id"],
        full_name=user["full_name"],
        email=security.decrypt_field(user["email"]),
        username=security.decrypt_field(user["username"]),
        phone_number=security.decrypt_field(phone["phone_number"]),
        status=user["status"],
    )


#Login

@router.post("/login", response_model=User_schemas.TokenResponse)
async def login(form_data: OAuth2PasswordRequestForm = Depends(), cur=Depends(get_db)):
    try:
        email = form_data.username
        user = await user_repository.authenticate_user(cur, email, form_data.password)
        if not user:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password")

        roles       = await user_repository.get_user_roles(cur, user["user_id"])
        permissions = await user_repository.get_user_permissions(cur, user["user_id"])
        access_token = security.create_access_token(data={"sub": user["user_id"]})
        refresh_token = await user_repository.create_refresh_token(cur, user["user_id"])

        return {
            "success": True,
            "message": "You are logged in successfully",
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer",
            "expires_in": security.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
            "user_id": user["user_id"],
            "full_name": user["full_name"],
            "email": security.decrypt_field(user["email"]),
            "roles": list(roles) if roles else [],
            "permissions": list(permissions) if permissions else [],
        }
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error")


#forgot Password
@router.post("/forgot-password")
async def forgot_password(payload: User_schemas.ForgotPasswordRequest, cur=Depends(get_db)):
    try:
        user = await user_repository.get_user_by_email_hmac(cur, payload.email)
        if not user:
            return {"message": "A link has been sent to your email, please check and copy the token"}

        raw_token, token_hash = security.generate_reset_token()
        expires_at = datetime.utcnow() + timedelta(minutes=10)
        await user_repository.create_password_reset(
            cur=cur, user_id=user["user_id"], token_hash=token_hash, expires_at=expires_at
        )
        reset_link = f"http://localhost:3000/reset-password/{raw_token}"

        if MAIL_ENABLED:
            html = f"""
            <h2>Password Reset</h2>
            <p>Click below to reset your password:</p>
            <a href="{reset_link}">Reset Password</a>
            <p>Link expires in 10 minutes.</p>
            """
            message = MessageSchema(
                subject="Password Reset Request",
                recipients=[payload.email],
                body=html,
                subtype="html",
            )
            fm = FastMail(mail_conf)
            await fm.send_message(message)
        else:
            print(f"\n>>> RESET TOKEN for {payload.email}: {raw_token}")
            print(f">>> RESET LINK: {reset_link}\n")

        return {
            "success": True,
            "message": "A link has been sent to your email, please check and copy the token.",
            "data": None,
        }
    except Exception:
        import traceback
        print("FORGOT PASSWORD ERROR:")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail="Internal server error")


#reset Password
@router.post("/reset-password")
async def reset_password(payload: User_schemas.ResetPasswordRequest, cur=Depends(get_db)):
    entry = await user_repository.validate_reset_token(cur, payload.token)
    if not entry:
        raise HTTPException(status_code=400, detail="Invalid or expired token")

    await user_repository.reset_user_password(cur, entry["rp_id"], entry["user_id"], payload.new_password)
    return {
        "success": True,
        "message": "Password has been reset successfully. Please login.",
        "data": None,
    }