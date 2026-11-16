from fastapi import APIRouter

from app.routers import auth, conversations, messages, notifications, users

# Every REST router is mounted under /api/v1 by app.main
api_router = APIRouter()
api_router.include_router(auth.router)
api_router.include_router(users.router)
api_router.include_router(conversations.router)
api_router.include_router(messages.router)
api_router.include_router(notifications.router)

__all__ = ["api_router"]
