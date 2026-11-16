import { useEffect, useMemo, useState } from "react";

import { api, ApiError } from "../api/client";
import type { ConversationType, User } from "../api/types";
import { useAuth } from "../context/AuthContext";
import { useChat } from "../context/ChatContext";
import { useToast } from "../context/ToastContext";
import { Avatar } from "./Avatar";
import { Icon } from "./Icons";
import { Modal } from "./Modal";

export function NewChatModal({
  open,
  onClose,
}: {
  open: boolean;
  onClose: () => void;
}) {
  const { user } = useAuth();
  const { createConversation } = useChat();
  const { toast } = useToast();

  const [mode, setMode] = useState<ConversationType>("direct");
  const [name, setName] = useState("");
  const [query, setQuery] = useState("");
  const [users, setUsers] = useState<User[]>([]);
  const [selected, setSelected] = useState<string[]>([]);
  const [loading, setLoading] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!open) return;
    setMode("direct");
    setName("");
    setQuery("");
    setSelected([]);
    setError(null);
  }, [open]);

  useEffect(() => {
    if (!open) return;
    let cancelled = false;
    setLoading(true);
    const timer = window.setTimeout(() => {
      api
        .listUsers(query.trim() || undefined)
        .then((list) => {
          if (!cancelled) setUsers(list);
        })
        .catch((caught) => {
          if (!cancelled) {
            setError(
              caught instanceof ApiError
                ? caught.message
                : "Could not load users",
            );
          }
        })
        .finally(() => {
          if (!cancelled) setLoading(false);
        });
    }, 250);

    return () => {
      cancelled = true;
      window.clearTimeout(timer);
    };
  }, [open, query]);

  const visibleUsers = useMemo(
    () => users.filter((candidate) => candidate.id !== user?.id),
    [users, user?.id],
  );

  if (!user) return null;

  const selectedUsers = visibleUsers.filter((candidate) =>
    selected.includes(candidate.id),
  );

  const changeMode = (next: ConversationType) => {
    setMode(next);
    setSelected([]);
    setError(null);
  };

  const toggle = (id: string) => {
    setError(null);
    setSelected((previous) => {
      if (mode === "direct") {
        return previous[0] === id ? [] : [id];
      }
      return previous.includes(id)
        ? previous.filter((item) => item !== id)
        : [...previous, id];
    });
  };

  const create = async () => {
    if (busy) return;
    setError(null);

    if (selected.length === 0) {
      setError("Choose at least one person.");
      return;
    }
    if (mode === "group" && !name.trim()) {
      setError("Give the group a name.");
      return;
    }

    setBusy(true);
    try {
      await createConversation({
        type: mode,
        name: mode === "group" ? name.trim() : null,
        member_ids: selected,
      });
      toast(mode === "group" ? "Group created" : "Conversation ready", "success");
      onClose();
    } catch (caught) {
      setError(
        caught instanceof ApiError
          ? caught.message
          : "Could not create the conversation",
      );
    } finally {
      setBusy(false);
    }
  };

  return (
    <Modal
      open={open}
      onClose={onClose}
      title="New conversation"
      subtitle="Message one person or gather a group"
      icon={<Icon name="plus" size={19} />}
      size="md"
      footer={
        <>
          <span className="modal__footer-hint">
            {mode === "direct"
              ? "Direct chats are reused if they already exist."
              : `${selected.length} selected`}
          </span>
          <button type="button" className="button button--ghost" onClick={onClose}>
            Cancel
          </button>
          <button
            type="button"
            className="button button--primary"
            onClick={() => void create()}
            disabled={busy || selected.length === 0}
          >
            {busy ? <span className="spinner" /> : <Icon name="chat" size={16} />}
            {mode === "group" ? "Create group" : "Start chat"}
          </button>
        </>
      }
    >
      <div className="segmented">
        <button
          type="button"
          className={mode === "direct" ? "is-active" : ""}
          onClick={() => changeMode("direct")}
        >
          <Icon name="user" size={16} /> Direct
        </button>
        <button
          type="button"
          className={mode === "group" ? "is-active" : ""}
          onClick={() => changeMode("group")}
        >
          <Icon name="users" size={16} /> Group
        </button>
      </div>

      {mode === "group" && (
        <label className="field field--compact">
          <span className="field__label">Group name</span>
          <span className="field__control">
            <Icon name="users" size={17} />
            <input
              value={name}
              onChange={(event) => {
                setName(event.target.value);
                setError(null);
              }}
              placeholder="Product team"
              maxLength={120}
              autoFocus
            />
          </span>
        </label>
      )}

      {selectedUsers.length > 0 && (
        <div className="chips">
          {selectedUsers.map((candidate) => (
            <button
              key={candidate.id}
              type="button"
              className="chip"
              onClick={() => toggle(candidate.id)}
              title={`Remove ${candidate.full_name}`}
            >
              <Avatar
                name={candidate.full_name}
                src={candidate.profile_picture_url}
                size="sm"
                className="chip__avatar"
              />
              {candidate.full_name}
              <Icon name="x" size={13} />
            </button>
          ))}
        </div>
      )}

      {error && (
        <div className="form-error" role="alert">
          <Icon name="warning" size={16} />
          <span>{error}</span>
        </div>
      )}

      <div className="person-picker">
        <div className="sidebar__search">
          <Icon name="search" size={17} />
          <input
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            placeholder="Search by name, username or email"
          />
        </div>

        <div className="person-picker__list">
          {loading ? (
            <div className="person-picker__status">
              <span className="spinner" /> Searching…
            </div>
          ) : visibleUsers.length === 0 ? (
            <div className="person-picker__status">
              {query ? "No people match that search." : "No other accounts yet."}
            </div>
          ) : (
            visibleUsers.map((candidate) => {
              const isSelected = selected.includes(candidate.id);
              return (
                <button
                  key={candidate.id}
                  type="button"
                  className={`person-row ${isSelected ? "is-selected" : ""}`}
                  onClick={() => toggle(candidate.id)}
                >
                  <Avatar
                    name={candidate.full_name}
                    src={candidate.profile_picture_url}
                    online={candidate.is_online}
                  />
                  <div className="person-row__identity">
                    <strong>{candidate.full_name}</strong>
                    <span>@{candidate.username}</span>
                  </div>
                  <span
                    className={`person-row__check ${
                      isSelected ? "is-selected" : ""
                    }`}
                  >
                    {isSelected ? (
                      <Icon name="check" size={14} />
                    ) : mode === "direct" ? (
                      <Icon name="chat" size={15} />
                    ) : (
                      <Icon name="plus" size={15} />
                    )}
                  </span>
                </button>
              );
            })
          )}
        </div>
      </div>
    </Modal>
  );
}
