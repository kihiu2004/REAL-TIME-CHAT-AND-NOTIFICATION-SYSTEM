import type { Notification } from "../api/types";
import { useChat } from "../context/ChatContext";
import { formatRelative } from "../lib/format";
import { Icon, type IconName } from "./Icons";

function iconFor(type: Notification["type"]): IconName {
  switch (type) {
    case "message":
      return "chat";
    case "mention":
      return "at";
    case "conversation_invite":
      return "users";
    default:
      return "bell";
  }
}

export function NotificationsPanel() {
  const {
    notificationsOpen,
    closeNotifications,
    notifications,
    unreadNotifications,
    markNotificationRead,
    markAllNotificationsRead,
    selectConversation,
  } = useChat();

  if (!notificationsOpen) return null;

  const openNotification = async (notification: Notification) => {
    if (!notification.is_read) await markNotificationRead(notification.id);
    const conversationId = notification.data?.conversation_id;
    if (typeof conversationId === "string") {
      closeNotifications();
      await selectConversation(conversationId);
    }
  };

  return (
    <div
      className="drawer-overlay"
      onMouseDown={(event) => {
        if (event.target === event.currentTarget) closeNotifications();
      }}
    >
      <aside className="drawer" role="dialog" aria-label="Notifications">
        <header className="drawer__header">
          <div>
            <h2>
              Notifications
              {unreadNotifications > 0 && (
                <span className="badge">{unreadNotifications}</span>
              )}
            </h2>
            <p>Realtime updates from your conversations</p>
          </div>
          <button
            type="button"
            className="icon-button"
            onClick={closeNotifications}
            aria-label="Close notifications"
          >
            <Icon name="x" size={18} />
          </button>
        </header>

        <div className="drawer__toolbar">
          <button
            type="button"
            className="button button--ghost button--small"
            onClick={() => void markAllNotificationsRead()}
            disabled={unreadNotifications === 0}
          >
            <Icon name="checkCheck" size={15} />
            Mark all as read
          </button>
        </div>

        <div className="drawer__body">
          {notifications.length === 0 ? (
            <div className="drawer__empty">
              <span className="drawer__empty-icon">
                <Icon name="bell" size={26} />
              </span>
              <h3>You are all caught up</h3>
              <p>New messages and mentions will show up here instantly.</p>
            </div>
          ) : (
            notifications.map((notification) => (
              <button
                key={notification.id}
                type="button"
                className={`notification-row ${
                  notification.is_read ? "" : "is-unread"
                }`}
                onClick={() => void openNotification(notification)}
              >
                <span className="notification-row__icon">
                  <Icon name={iconFor(notification.type)} size={18} />
                </span>
                <span className="notification-row__body">
                  <span className="notification-row__top">
                    <strong>{notification.title}</strong>
                    <time dateTime={notification.created_at}>
                      {formatRelative(notification.created_at)}
                    </time>
                  </span>
                  {notification.body && <p>{notification.body}</p>}
                </span>
                {!notification.is_read && (
                  <span className="notification-row__dot" aria-label="Unread" />
                )}
              </button>
            ))
          )}
        </div>
      </aside>
    </div>
  );
}
