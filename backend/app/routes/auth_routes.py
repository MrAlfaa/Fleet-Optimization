from fastapi import APIRouter, Depends

from app.middleware.auth_middleware import get_current_user
from app.schemas.auth_schema import ChangePasswordRequest, LoginRequest, RegisterRequest
from app.services.auth_service import authenticate_user, change_password, register_user
from app.utils.response import success_response


router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/register")
async def register(payload: RegisterRequest) -> dict:
    data = await register_user(payload.model_dump())
    return success_response("Registration successful", data=data)


@router.post("/login")
async def login(payload: LoginRequest) -> dict:
    data = await authenticate_user(str(payload.email), payload.password)
    return success_response("Login successful", data=data)


@router.get("/me")
async def me(current_user: dict = Depends(get_current_user)) -> dict:
    return success_response("Current user loaded", data=current_user)


@router.post("/change-password")
async def update_password(
    payload: ChangePasswordRequest,
    current_user: dict = Depends(get_current_user),
) -> dict:
    user = await change_password(current_user["id"], payload.old_password, payload.new_password)
    return success_response("Password changed successfully", data=user)


@router.post("/logout")
async def logout(current_user: dict = Depends(get_current_user)) -> dict:
    return success_response("Logout successful", data={"token_revoked": False})
