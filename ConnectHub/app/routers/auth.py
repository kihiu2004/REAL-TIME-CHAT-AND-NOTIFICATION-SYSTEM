from fastapi import APIRouter, status

from app.core.deps import CurrentUser, DbSession
from app.core.jwt import create_access_token
from app.schemas.auth import AuthResponse, LoginRequest, RegisterRequest
from app.schemas.user import UserPublic
from app.services import auth_service

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post(
    "/register",
    response_model=AuthResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create an account",
)
async def register(payload: RegisterRequest, db: DbSession) -> AuthResponse:
    user = await auth_service.register_user(db, payload)
    return AuthResponse(
        access_token=create_access_token(user.id),
        user=UserPublic.model_validate(user),
    )


@router.post("/login", response_model=AuthResponse, summary="Log in")
async def login(payload: LoginRequest, db: DbSession) -> AuthResponse:
    user = await auth_service.authenticate(db, payload.identifier, payload.password)
    return AuthResponse(
        access_token=create_access_token(user.id),
        user=UserPublic.model_validate(user),
    )


@router.get("/me", response_model=UserPublic, summary="Current account")
async def read_me(user: CurrentUser) -> UserPublic:
    return UserPublic.model_validate(user)
