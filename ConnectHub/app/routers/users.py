import uuid

from fastapi import APIRouter, Query

from app.core.deps import CurrentUser, DbSession
from app.schemas.user import UserPublic, UserUpdate
from app.services import user_service

router = APIRouter(prefix="/users", tags=["users"])


@router.get("/me", response_model=UserPublic, summary="My profile")
async def read_my_profile(user: CurrentUser) -> UserPublic:
    return UserPublic.model_validate(user)


@router.patch("/me", response_model=UserPublic, summary="Update my profile")
async def update_my_profile(
    payload: UserUpdate,
    db: DbSession,
    user: CurrentUser,
) -> UserPublic:
    updated = await user_service.update_profile(db, user, payload)
    return UserPublic.model_validate(updated)


@router.get("", response_model=list[UserPublic], summary="List users")
async def list_users(
    db: DbSession,
    user: CurrentUser,
    q: str | None = Query(default=None, max_length=100, description="Search text"),
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
) -> list[UserPublic]:
    users = await user_service.list_users(db, search=q, limit=limit, offset=offset)
    return [UserPublic.model_validate(item) for item in users]


@router.get("/{user_id}", response_model=UserPublic, summary="Get one user")
async def read_user(user_id: uuid.UUID, db: DbSession, user: CurrentUser) -> UserPublic:
    found = await user_service.get_user(db, user_id)
    return UserPublic.model_validate(found)
