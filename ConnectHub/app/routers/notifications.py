import uuid

from fastapi import APIRouter, Query

from app.core.deps import CurrentUser, DbSession
from app.schemas.notification import NotificationPage, NotificationPublic, UnreadCount
from app.services import notification_service

router = APIRouter(prefix="/notifications", tags=["notifications"])


@router.get("", response_model=NotificationPage, summary="My notifications")
async def list_notifications(
    db: DbSession,
    user: CurrentUser,
    unread_only: bool = Query(default=False),
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
) -> NotificationPage:
    return await notification_service.list_notifications(
        db,
        user.id,
        unread_only=unread_only,
        limit=limit,
        offset=offset,
    )


@router.get("/unread-count", response_model=UnreadCount, summary="Unread count")
async def unread_count(db: DbSession, user: CurrentUser) -> UnreadCount:
    return UnreadCount(unread_count=await notification_service.unread_count(db, user.id))


@router.post("/read-all", response_model=UnreadCount, summary="Mark all as read")
async def mark_all_read(db: DbSession, user: CurrentUser) -> UnreadCount:
    await notification_service.mark_all_read(db, user.id)
    return UnreadCount(unread_count=await notification_service.unread_count(db, user.id))


@router.post(
    "/{notification_id}/read",
    response_model=NotificationPublic,
    summary="Mark one as read",
)
async def mark_read(
    notification_id: uuid.UUID,
    db: DbSession,
    user: CurrentUser,
) -> NotificationPublic:
    notification = await notification_service.mark_read(db, user.id, notification_id)
    return NotificationPublic.model_validate(notification)
