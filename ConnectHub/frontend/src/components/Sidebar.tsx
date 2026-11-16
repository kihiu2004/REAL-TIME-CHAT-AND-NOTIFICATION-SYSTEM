import { useMemo, useState } from "react";

import type { ConversationListItem } from "../api/types";
import { useAuth } from "../context/AuthContext";
import { useChat } from "../context/ChatContext";
import {
  conversationTitle,
  formatListTime,
  otherMember,
} from "../lib/format";
import { Avatar } from "./Avatar";
import { Icon } from "./Icons";

export function Sidebar({
  onNewChat,
  onProfile,
}: {
  onNewChat: () => void;
  onProfile: () => void;
}) {
  const { user, logout } = useAuth();
  const {
    conversations,
    activeId,
    selectConversation,
    unreadNotifications,
    openNotifications,
    connectionState,
    isOnline,
  } = useChat();
  const [query, setQuery] = useState("");
  const currentUserId = user?.id ?? "";

  const filtered = useMemo(() => {
    const needle = query.trim().toLowerCase();
    if (!needle) return conversations;
    return conversations.filter((conversation) => {
      const title = conversationTitle(conversation, currentUserId).toLowerCase();
      const names = conversation.members
        .map((member) => `${member.user.full_name} ${member.user.username}`)
        .join(" ")
        .toLowerCase();
      const preview = conversation.last_message?.content?.toLowerCase() ?? "";
      return (
        title.includes(needle) ||
        names.includes(needle) ||
        preview.includes(needle)
      );
    });
  }, [conversations, query, currentUserId]);

  if (!user) return null;

  return (
    <aside className="sidebar">
      <header className="sidebar__header">
        <div className="brand">
          <span className="brand__mark">
            <Icon name="chat" size={19} />
          </span>
          <span className="brand__name">ConnectHub</span>
        </div>

        <div className="sidebar__actions">
          <button
            type="button"
            className="icon-button"
            aria-label={`Notifications${
              unreadNotifications ? ` (${unreadNotifications} unread)` : ""
            }`}
            title="Notifications"
            onClick={openNotifications}
          >
            <Icon name="bell" size={19} />
            {unreadNotifications > 0 && (
              <span className="badge badge--dot">
                {unreadNotifications > 99 ? "99+" : unreadNotifications}
              </span>
            )}
          </button>
          <button
            type="button"
            className="icon-button"
            aria-label="My profile"
            title="My profile"
            onClick={onProfile}
          >
            <Icon name="user" size={19} />
          </button>
          <button
            type="button"
            className="icon-button"
            aria-label="Sign out"
            title="Sign out"
            onClick={logout}
          >
            <Icon name="logout" size={19} />
          </button>
        </div>
      </header>

      <div className="sidebar__search">
        <Icon name="search" size={17} />
        <input
          value={query}
          onChange={(event) => setQuery(event.target.value)}
          placeholder="Search conversations"
          aria-label="Search conversations"
        />
        {query && (
          <button
            type="button"
            className="sidebar__search-clear"
            onClick={() => setQuery("")}
            aria-label="Clear search"
          >
            <Icon name="x" size={14} />
          </button>
        )}
      </div>

      <div className="sidebar__section">
        <span>Messages</span>
        <button type="button" className="button button--ghost button--small" onClick={onNewChat}>
          <Icon name="plus" size={15} />
          New chat
        </button>
      </div>

      <div className="conversation-list" role="list">
        {filtered.length === 0 ? (
          <div className="conversation-list__empty">
            <Icon name="chat" size={26} />
            <p>{query ? "No conversations match that search." : "No conversations yet."}</p>
            {!query && (
              <button type="button" className="link" onClick={onNewChat}>
                Start your first chat
              </button>
            )}
          </div>
        ) : (
          filtered.map((conversation) => (
            <ConversationRow
              key={conversation.id}
              conversation={conversation}
              currentUserId={user.id}
              active={conversation.id === activeId}
              isOnline={isOnline}
              onSelect={() => void selectConversation(conversation.id)}
            />
          ))
        )}
      </div>

      <footer className="sidebar__footer">
        <Avatar
          name={user.full_name}
          src={user.profile_picture_url}
          size="sm"
          online
        />
        <div className="sidebar__me">
          <strong>{user.full_name}</strong>
          <span>@{user.username}</span>
        </div>
        <span
          className={`connection-chip connection-chip--${connectionState}`}
          title={
            connectionState === "open"
              ? "Realtime connection is live"
              : "Reconnecting to the realtime server"
          }
        >
          <span className="connection-chip__dot" />
          {connectionState === "open"
            ? "Live"
            : connectionState === "connecting"
              ? "Connecting"
              : "Offline"}
        </span>
      </footer>
    </aside>
  );
}

function ConversationRow({
  conversation,
  currentUserId,
  active,
  isOnline,
  onSelect,
}: {
  conversation: ConversationListItem;
  currentUserId: string;
  active: boolean;
  isOnline: (user: ConversationListItem["members"][number]["user"]) => boolean;
  onSelect: () => void;
}) {
  const title = conversationTitle(conversation, currentUserId);
  const other = otherMember(conversation, currentUserId);
  const online =
    conversation.type === "direct" && other ? isOnline(other.user) : undefined;
  const preview = conversation.last_message;
  const mine = preview?.sender_id === currentUserId;
  const unread = conversation.unread_count > 0;

  return (
    <button
      type="button"
      role="listitem"
      className={`conversation-row ${active ? "is-active" : ""} ${
        unread ? "has-unread" : ""
      }`}
      onClick={onSelect}
      aria-current={active ? "true" : undefined}
    >
      <Avatar
        name={title}
        src={conversation.type === "direct" ? other?.user.profile_picture_url : null}
        variant={conversation.type === "group" ? "group" : "user"}
        online={online}
      />
      <div className="conversation-row__body">
        <div className="conversation-row__top">
          <span className="conversation-row__name">{title}</span>
          <span className="conversation-row__time">
            {formatListTime(preview?.created_at ?? conversation.updated_at)}
          </span>
        </div>
        <div className="conversation-row__bottom">
          <span className="conversation-row__preview">
            {mine && preview ? "You: " : ""}
            {preview?.content || "No messages yet"}
          </span>
          {unread && (
            <span className="badge">
              {conversation.unread_count > 99 ? "99+" : conversation.unread_count}
            </span>
          )}
        </div>
      </div>
    </button>
  );
}
