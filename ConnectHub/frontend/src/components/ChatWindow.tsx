import { useEffect, useState } from "react";

import type { Message } from "../api/types";
import { useAuth } from "../context/AuthContext";
import { useChat } from "../context/ChatContext";
import {
  conversationSubtitle,
  conversationTitle,
  formatLastSeen,
  otherMember,
} from "../lib/format";
import { Avatar } from "./Avatar";
import { Composer } from "./Composer";
import { EmptyState } from "./EmptyState";
import { GroupInfoModal } from "./GroupInfoModal";
import { Icon } from "./Icons";
import { MessageList } from "./MessageList";

export function ChatWindow({
  onBack,
  onNewChat,
}: {
  onBack: () => void;
  onNewChat: () => void;
}) {
  const { user } = useAuth();
  const {
    activeConversation,
    messages,
    typingUsers,
    loadingMessages,
    loadingMore,
    hasMoreMessages,
    loadOlderMessages,
    sendMessage,
    editMessage,
    deleteMessage,
    setTyping,
    isOnline,
    connectionState,
  } = useChat();
  const [replyTo, setReplyTo] = useState<Message | null>(null);
  const [infoOpen, setInfoOpen] = useState(false);

  const conversationId = activeConversation?.id ?? null;

  useEffect(() => {
    setReplyTo(null);
  }, [conversationId]);

  if (!user) return null;

  if (!activeConversation) {
    return (
      <section className="chat chat--empty">
        <EmptyState onNewChat={onNewChat} />
      </section>
    );
  }

  const conversation = activeConversation;
  const title = conversationTitle(conversation, user.id);
  const other = otherMember(conversation, user.id);
  const online =
    conversation.type === "direct" && other ? isOnline(other.user) : undefined;
  const onlineCount = conversation.members.filter((member) =>
    isOnline(member.user),
  ).length;

  const subtitle =
    conversation.type === "direct"
      ? online
        ? "Online now"
        : formatLastSeen(other?.user.last_seen_at ?? null)
      : `${conversationSubtitle(conversation, user.id)} · ${onlineCount} online`;

  const handleSend = async (content: string) => {
    const ok = await sendMessage(content, replyTo?.id ?? null);
    if (ok) setReplyTo(null);
    return ok;
  };

  const handleDelete = (message: Message) => {
    if (window.confirm("Delete this message for everyone?")) {
      void deleteMessage(message.id);
    }
  };

  return (
    <section className="chat">
      <header className="chat__header">
        <button
          type="button"
          className="icon-button chat__back"
          onClick={onBack}
          aria-label="Back to conversations"
          title="Back to conversations"
        >
          <Icon name="arrowLeft" size={20} />
        </button>

        <Avatar
          name={title}
          src={conversation.type === "direct" ? other?.user.profile_picture_url : null}
          variant={conversation.type === "group" ? "group" : "user"}
          online={online}
        />

        <div className="chat__identity">
          <h1>{title}</h1>
          <p>
            {conversation.type === "direct" && (
              <span
                className={`presence-dot ${
                  online ? "is-online" : "is-offline"
                }`}
              />
            )}
            {subtitle}
          </p>
        </div>

        <div className="chat__header-actions">
          <span
            className={`connection-chip connection-chip--${connectionState}`}
            title="Realtime connection status"
          >
            <span className="connection-chip__dot" />
            {connectionState === "open" ? "Live" : "Reconnecting"}
          </span>
          <button
            type="button"
            className="icon-button"
            onClick={() => setInfoOpen(true)}
            aria-label="Conversation details"
            title="Conversation details"
          >
            <Icon name="info" size={19} />
          </button>
        </div>
      </header>

      {loadingMessages ? (
        <div className="chat__loading">
          <span className="spinner spinner--large" />
          <p>Loading messages…</p>
        </div>
      ) : (
        <MessageList
          conversation={conversation}
          messages={messages}
          currentUserId={user.id}
          hasMore={hasMoreMessages}
          loadingMore={loadingMore}
          typingUsers={typingUsers}
          onLoadOlder={() => void loadOlderMessages()}
          onReply={setReplyTo}
          onEdit={editMessage}
          onDelete={handleDelete}
        />
      )}

      <Composer
        key={conversation.id}
        onSend={handleSend}
        onTyping={setTyping}
        replyTo={replyTo}
        onCancelReply={() => setReplyTo(null)}
      />

      <GroupInfoModal open={infoOpen} onClose={() => setInfoOpen(false)} />
    </section>
  );
}
