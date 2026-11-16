import {
  Fragment,
  useEffect,
  useRef,
  useState,
  type FormEvent,
} from "react";

import type { ConversationListItem, Message } from "../api/types";
import {
  classNames,
  formatClock,
  formatDay,
  isSameGroupDay,
  formatRelative,
} from "../lib/format";
import { Avatar } from "./Avatar";
import { Icon } from "./Icons";

export function MessageList({
  conversation,
  messages,
  currentUserId,
  hasMore,
  loadingMore,
  typingUsers,
  onLoadOlder,
  onReply,
  onEdit,
  onDelete,
}: {
  conversation: ConversationListItem;
  messages: Message[];
  currentUserId: string;
  hasMore: boolean;
  loadingMore: boolean;
  typingUsers: string[];
  onLoadOlder: () => void;
  onReply: (message: Message) => void;
  onEdit: (messageId: string, content: string) => Promise<boolean>;
  onDelete: (message: Message) => void;
}) {
  const containerRef = useRef<HTMLDivElement | null>(null);
  const atBottomRef = useRef(true);
  const previousConversationRef = useRef("");
  const previousLengthRef = useRef(0);
  const pendingRestoreRef = useRef<{ height: number; top: number } | null>(null);

  const myMembership = conversation.members.find(
    (member) => member.user.id === currentUserId,
  );
  const canManage =
    myMembership?.role === "owner" || myMembership?.role === "admin";

  const otherMembers = conversation.members.filter(
    (member) => member.user.id !== currentUserId,
  );

  const lastOwn = [...messages]
    .reverse()
    .find((message) => message.sender?.id === currentUserId);
  const readers = lastOwn
    ? otherMembers.filter(
        (member) =>
          member.last_read_at &&
          new Date(member.last_read_at).getTime() >=
            new Date(lastOwn.created_at).getTime(),
      )
    : [];
  const receipt = lastOwn
    ? readers.length === 0
      ? undefined
      : conversation.type === "direct"
        ? "Seen"
        : `Seen by ${readers.length}`
    : undefined;

  useEffect(() => {
    const element = containerRef.current;
    if (!element) return;

    if (previousConversationRef.current !== conversation.id) {
      previousConversationRef.current = conversation.id;
      previousLengthRef.current = messages.length;
      atBottomRef.current = true;
      pendingRestoreRef.current = null;
      requestAnimationFrame(() => {
        element.scrollTop = element.scrollHeight;
      });
      return;
    }

    if (previousLengthRef.current === messages.length) return;

    const previousLength = previousLengthRef.current;
    previousLengthRef.current = messages.length;

    if (pendingRestoreRef.current) {
      const { height, top } = pendingRestoreRef.current;
      pendingRestoreRef.current = null;
      element.scrollTop = element.scrollHeight - height + top;
      return;
    }

    const last = messages[messages.length - 1];
    const ownMessage = last?.sender?.id === currentUserId;
    const appended = messages.length > previousLength;

    if (atBottomRef.current || (appended && ownMessage)) {
      requestAnimationFrame(() => {
        element.scrollTo({ top: element.scrollHeight, behavior: "smooth" });
      });
    }
  }, [conversation.id, messages, currentUserId]);

  const handleLoadOlder = () => {
    const element = containerRef.current;
    if (element) {
      pendingRestoreRef.current = {
        height: element.scrollHeight,
        top: element.scrollTop,
      };
    }
    onLoadOlder();
  };

  return (
    <div
      className="messages"
      ref={containerRef}
      onScroll={(event) => {
        const element = event.currentTarget;
        atBottomRef.current =
          element.scrollHeight - element.scrollTop - element.clientHeight < 140;
      }}
    >
      {hasMore && (
        <div className="messages__older">
          <button
            type="button"
            className="button button--ghost button--small"
            onClick={handleLoadOlder}
            disabled={loadingMore}
          >
            {loadingMore ? <span className="spinner" /> : <Icon name="clock" size={15} />}
            {loadingMore ? "Loading…" : "Load older messages"}
          </button>
        </div>
      )}

      {messages.length === 0 && (
        <div className="messages__empty">
          <span className="messages__empty-icon">
            <Icon name="chat" size={28} />
          </span>
          <h3>No messages yet</h3>
          <p>Say hello and start the conversation.</p>
        </div>
      )}

      {messages.map((message, index) => {
        const previous = messages[index - 1];
        const showDay =
          !previous || !isSameGroupDay(previous.created_at, message.created_at);
        const sameSender =
          previous &&
          previous.sender?.id === message.sender?.id &&
          sameSenderWindow(previous.created_at, message.created_at);
        const showName =
          conversation.type === "group" &&
          message.sender?.id !== currentUserId &&
          !sameSender;
        const showAvatar =
          conversation.type === "group" &&
          message.sender?.id !== currentUserId &&
          !sameSender;
        const mine = message.sender?.id === currentUserId;
        const replyTarget = message.reply_to_id
          ? messages.find((item) => item.id === message.reply_to_id)
          : undefined;

        if (message.message_type === "system") {
          return (
            <Fragment key={message.id}>
              {showDay && <DaySeparator value={message.created_at} />}
              <div className="system-message">{message.content}</div>
            </Fragment>
          );
        }

        return (
          <Fragment key={message.id}>
            {showDay && <DaySeparator value={message.created_at} />}
            <div
              className={classNames(
                "message-row",
                mine && "is-mine",
                showAvatar && "has-avatar",
              )}
            >
              {!mine && showAvatar ? (
                <Avatar
                  name={message.sender?.full_name ?? "Unknown"}
                  src={message.sender?.profile_picture_url}
                  size="sm"
                />
              ) : (
                !mine && <span className="message-row__spacer" />
              )}

              <div className="message-row__main">
                {showName && (
                  <span className="message-row__sender">
                    {message.sender?.full_name ?? "Unknown"}
                  </span>
                )}

                <div className="message-row__bubble-line">
                  {!mine && (
                    <MessageActions
                      mine={false}
                      canDelete={canManage}
                      onReply={() => onReply(message)}
                      onDelete={() => onDelete(message)}
                    />
                  )}

                  <MessageBubble
                    message={message}
                    mine={mine}
                    replyTarget={replyTarget}
                    receipt={message.id === lastOwn?.id ? receipt : undefined}
                    canEdit={mine && message.message_type === "text"}
                    onEdit={onEdit}
                  />

                  {mine && (
                    <MessageActions
                      mine
                      canDelete
                      onReply={() => onReply(message)}
                      onDelete={() => onDelete(message)}
                    />
                  )}
                </div>
              </div>
            </div>
          </Fragment>
        );
      })}

      {typingUsers.length > 0 && (
        <div className="typing-row">
          <div className="typing-dots" aria-hidden="true">
            <span />
            <span />
            <span />
          </div>
          <span>
            {typingUsers.length === 1
              ? `${typingUsers[0]} is typing…`
              : `${typingUsers.slice(0, 2).join(" and ")} are typing…`}
          </span>
        </div>
      )}
    </div>
  );
}

function DaySeparator({ value }: { value: string }) {
  return (
    <div className="day-separator">
      <span>{formatDay(value)}</span>
    </div>
  );
}

function sameSenderWindow(a: string, b: string): boolean {
  return Math.abs(new Date(b).getTime() - new Date(a).getTime()) < 5 * 60_000;
}

function MessageActions({
  mine,
  canDelete,
  onReply,
  onDelete,
}: {
  mine: boolean;
  canDelete: boolean;
  onReply: () => void;
  onDelete: () => void;
}) {
  return (
    <div className={classNames("message-actions", mine && "message-actions--mine")}>
      <button type="button" title="Reply" aria-label="Reply" onClick={onReply}>
        <Icon name="reply" size={15} />
      </button>
      {canDelete && (
        <button
          type="button"
          title="Delete"
          aria-label="Delete"
          className="is-danger"
          onClick={onDelete}
        >
          <Icon name="trash" size={14} />
        </button>
      )}
    </div>
  );
}

function MessageBubble({
  message,
  mine,
  replyTarget,
  receipt,
  canEdit,
  onEdit,
}: {
  message: Message;
  mine: boolean;
  replyTarget?: Message;
  receipt?: string;
  canEdit: boolean;
  onEdit: (messageId: string, content: string) => Promise<boolean>;
}) {
  const [editing, setEditing] = useState(false);
  const [draft, setDraft] = useState(message.content ?? "");
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    setDraft(message.content ?? "");
  }, [message.content]);

  const submit = async (event: FormEvent) => {
    event.preventDefault();
    const value = draft.trim();
    if (!value || saving) return;
    setSaving(true);
    const ok = await onEdit(message.id, value);
    setSaving(false);
    if (ok) setEditing(false);
  };

  return (
    <div
      className={classNames(
        "bubble",
        mine ? "bubble--mine" : "bubble--theirs",
        editing && "bubble--editing",
      )}
    >
      {replyTarget && (
        <div className="bubble__reply">
          <span>
            {replyTarget.sender?.full_name ?? "Unknown"}{" "}
            {formatRelative(replyTarget.created_at)}
          </span>
          <p>{replyTarget.content || "Message"}</p>
        </div>
      )}

      {editing ? (
        <form className="bubble__edit" onSubmit={submit}>
          <textarea
            value={draft}
            onChange={(event) => setDraft(event.target.value)}
            rows={2}
            autoFocus
            maxLength={4000}
            onKeyDown={(event) => {
              if (event.key === "Escape") setEditing(false);
            }}
          />
          <div className="bubble__edit-actions">
            <button
              type="button"
              className="button button--ghost button--small"
              onClick={() => {
                setDraft(message.content ?? "");
                setEditing(false);
              }}
            >
              Cancel
            </button>
            <button
              type="submit"
              className="button button--primary button--small"
              disabled={saving || !draft.trim()}
            >
              {saving ? "Saving…" : "Save"}
            </button>
          </div>
        </form>
      ) : (
        <p className="bubble__text">{message.content}</p>
      )}

      <div className="bubble__meta">
        {message.is_edited && <span className="bubble__edited">edited</span>}
        <time dateTime={message.created_at}>{formatClock(message.created_at)}</time>
        {receipt && (
          <span className="bubble__receipt" title={receipt}>
            <Icon name="checkCheck" size={14} />
            {receipt}
          </span>
        )}
        {canEdit && !editing && (
          <button
            type="button"
            className="bubble__edit-trigger"
            aria-label="Edit message"
            title="Edit message"
            onClick={() => {
              setDraft(message.content ?? "");
              setEditing(true);
            }}
          >
            <Icon name="edit" size={13} />
          </button>
        )}
      </div>
    </div>
  );
}
