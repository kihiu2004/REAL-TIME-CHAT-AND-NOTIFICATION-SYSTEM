# Importing every model here registers it on Base.metadata, which is what
# Alembic (migrations/env.py) relies on for autogeneration.
from app.models.conversation import Conversation, ConversationType
from app.models.conversation_member import ConversationMember, MemberRole
from app.models.message import Message, MessageType
from app.models.message_read import MessageRead
from app.models.notification import Notification, NotificationType
from app.models.user import User, UserStatus

__all__ = [
    "Conversation",
    "ConversationMember",
    "ConversationType",
    "MemberRole",
    "Message",
    "MessageRead",
    "MessageType",
    "Notification",
    "NotificationType",
    "User",
    "UserStatus",
]
