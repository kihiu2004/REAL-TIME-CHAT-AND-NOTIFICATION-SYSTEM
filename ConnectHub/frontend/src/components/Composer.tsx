import { useEffect, useRef, useState } from "react";

import type { Message } from "../api/types";
import { Icon } from "./Icons";

export function Composer({
  onSend,
  onTyping,
  replyTo,
  onCancelReply,
}: {
  onSend: (content: string) => Promise<boolean>;
  onTyping: (isTyping: boolean) => void;
  replyTo: Message | null;
  onCancelReply: () => void;
}) {
  const [draft, setDraft] = useState("");
  const [sending, setSending] = useState(false);
  const textareaRef = useRef<HTMLTextAreaElement | null>(null);
  const typingRef = useRef(false);
  const typingTimerRef = useRef<number | undefined>(undefined);

  const resize = () => {
    const element = textareaRef.current;
    if (!element) return;
    element.style.height = "0px";
    element.style.height = `${Math.min(element.scrollHeight, 160)}px`;
  };

  useEffect(() => {
    resize();
  }, [draft]);

  useEffect(() => {
    if (replyTo) textareaRef.current?.focus();
  }, [replyTo]);

  const stopTyping = () => {
    if (typingTimerRef.current) {
      window.clearTimeout(typingTimerRef.current);
      typingTimerRef.current = undefined;
    }
    if (typingRef.current) {
      typingRef.current = false;
      onTyping(false);
    }
  };

  useEffect(() => {
    return () => {
      if (typingTimerRef.current) window.clearTimeout(typingTimerRef.current);
      if (typingRef.current) onTyping(false);
    };
    // Only run on unmount; onTyping is stable for the lifetime of the provider.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const handleChange = (value: string) => {
    setDraft(value);
    if (value.trim()) {
      if (!typingRef.current) {
        typingRef.current = true;
        onTyping(true);
      }
      if (typingTimerRef.current) window.clearTimeout(typingTimerRef.current);
      typingTimerRef.current = window.setTimeout(stopTyping, 2500);
    } else {
      stopTyping();
    }
  };

  const submit = async () => {
    const value = draft.trim();
    if (!value || sending) return;
    setSending(true);
    const ok = await onSend(value);
    setSending(false);
    if (ok) {
      setDraft("");
      stopTyping();
      requestAnimationFrame(() => textareaRef.current?.focus());
    }
  };

  return (
    <div className="composer">
      {replyTo && (
        <div className="composer__reply">
          <span className="composer__reply-bar" aria-hidden="true" />
          <div className="composer__reply-body">
            <span>Replying to {replyTo.sender?.full_name ?? "Unknown"}</span>
            <p>{replyTo.content?.slice(0, 120) || "Message"}</p>
          </div>
          <button
            type="button"
            className="icon-button"
            onClick={onCancelReply}
            aria-label="Cancel reply"
            title="Cancel reply"
          >
            <Icon name="x" size={16} />
          </button>
        </div>
      )}

      <div className="composer__box">
        <textarea
          ref={textareaRef}
          value={draft}
          rows={1}
          maxLength={4000}
          placeholder="Write a message…"
          aria-label="Message"
          onChange={(event) => handleChange(event.target.value)}
          onKeyDown={(event) => {
            if (event.key === "Enter" && !event.shiftKey) {
              event.preventDefault();
              void submit();
            }
          }}
        />

        <button
          type="button"
          className="composer__send"
          onClick={() => void submit()}
          disabled={!draft.trim() || sending}
          aria-label="Send message"
          title="Send message (Enter)"
        >
          {sending ? <span className="spinner" /> : <Icon name="send" size={18} />}
        </button>
      </div>

      <div className="composer__footer">
        <span>
          <kbd>Enter</kbd> to send · <kbd>Shift</kbd> + <kbd>Enter</kbd> for a
          new line
        </span>
        {draft.length > 3600 && (
          <span className={draft.length >= 4000 ? "is-limit" : ""}>
            {draft.length}/4000
          </span>
        )}
      </div>
    </div>
  );
}
