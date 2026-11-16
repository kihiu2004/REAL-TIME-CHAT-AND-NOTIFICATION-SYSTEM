import { useEffect, useMemo, useState, type FormEvent } from "react";

import { api } from "../api/client";
import type { Member, User } from "../api/types";
import { useAuth } from "../context/AuthContext";
import { useChat } from "../context/ChatContext";
import { useToast } from "../context/ToastContext";
import {
  conversationTitle,
  formatLastSeen,
  formatRelative,
  otherMember,
  roleLabel,
} from "../lib/format";
import { Avatar } from "./Avatar";
import { Icon } from "./Icons";
import { Modal } from "./Modal";

const ROLE_ORDER: Record<Member["role"], number> = {
  owner: 0,
  admin: 1,
  member: 2,
};

export function GroupInfoModal({
  open,
  onClose,
}: {
  open: boolean;
  onClose: () => void;
}) {
  const { user } = useAuth();
  const { toast } = useToast();
  const {
    activeConversation: conversation,
    renameConversation,
    addMember,
    removeMember,
    isOnline,
  } = useChat();

  const [name, setName] = useState("");
  const [renaming, setRenaming] = useState(false);
  const [showAdd, setShowAdd] = useState(false);
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<User[]>([]);
  const [searching, setSearching] = useState(false);
  const [busyUserId, setBusyUserId] = useState<string | null>(null);
  const [leaving, setLeaving] = useState(false);

  const conversationId = conversation?.id;

  useEffect(() => {
    if (!open) return;
    setName(conversation?.name ?? "");
    setShowAdd(false);
    setQuery("");
    setResults([]);
    // Reset only when the dialog opens or switches conversation.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [open, conversationId]);

  useEffect(() => {
    if (!open || !showAdd) return;
    let cancelled = false;
    setSearching(true);
    const timer = window.setTimeout(() => {
      api
        .listUsers(query.trim())
        .then((users) => {
          if (!cancelled) setResults(users);
        })
        .catch(() => {
          if (!cancelled) setResults([]);
        })
        .finally(() => {
          if (!cancelled) setSearching(false);
        });
    }, 250);

    return () => {
      cancelled = true;
      window.clearTimeout(timer);
    };
  }, [open, showAdd, query]);

  const members = useMemo(() => {
    if (!conversation) return [];
    return [...conversation.members].sort((a, b) => {
      const roleDelta = ROLE_ORDER[a.role] - ROLE_ORDER[b.role];
      if (roleDelta !== 0) return roleDelta;
      return a.user.full_name.localeCompare(b.user.full_name);
    });
  }, [conversation]);

  if (!conversation || !user) return null;

  const title = conversationTitle(conversation, user.id);
  const other = otherMember(conversation, user.id);
  const isGroup = conversation.type === "group";
  const mine = conversation.members.find((member) => member.user.id === user.id);
  const canManage = mine?.role === "owner" || mine?.role === "admin";
  const memberIds = new Set(conversation.members.map((member) => member.user.id));
  const candidates = results.filter(
    (candidate) => candidate.id !== user.id && !memberIds.has(candidate.id),
  );

  const submitRename = async (event: FormEvent) => {
    event.preventDefault();
    if (!name.trim() || name.trim() === conversation.name || renaming) return;
    setRenaming(true);
    try {
      await renameConversation(conversation.id, name.trim());
    } catch {
      // The chat context already surfaced the error.
    } finally {
      setRenaming(false);
    }
  };

  const handleAdd = async (candidate: User) => {
    setBusyUserId(candidate.id);
    try {
      await addMember(conversation.id, candidate.id);
      setResults((previous) => previous.filter((item) => item.id !== candidate.id));
    } catch {
      // Error already surfaced.
    } finally {
      setBusyUserId(null);
    }
  };

  const handleRemove = async (member: Member) => {
    const isSelf = member.user.id === user.id;
    const message = isSelf
      ? "Leave this conversation?"
      : `Remove ${member.user.full_name} from the conversation?`;
    if (!window.confirm(message)) return;

    if (isSelf) setLeaving(true);
    else setBusyUserId(member.user.id);
    try {
      await removeMember(conversation.id, member.user.id);
      if (isSelf) onClose();
    } catch {
      // Error already surfaced.
    } finally {
      setLeaving(false);
      setBusyUserId(null);
    }
  };

  return (
    <Modal
      open={open}
      onClose={onClose}
      title={isGroup ? "Group details" : "Conversation details"}
      subtitle={
        isGroup
          ? "Members, roles and group settings"
          : "Direct message details"
      }
      icon={<Icon name={isGroup ? "users" : "chat"} size={19} />}
      size="md"
    >
      <div className="details-hero">
        <Avatar
          name={title}
          src={isGroup ? null : other?.user.profile_picture_url}
          variant={isGroup ? "group" : "user"}
          size="xl"
          online={isGroup ? undefined : other ? isOnline(other.user) : undefined}
        />
        <div>
          <h3>{title}</h3>
          <p>
            {isGroup
              ? `${conversation.members.length} member${
                  conversation.members.length === 1 ? "" : "s"
                }`
              : `@${other?.user.username ?? "unknown"} · ${
                  other && isOnline(other.user)
                    ? "Online now"
                    : formatLastSeen(other?.user.last_seen_at ?? null)
                }`}
          </p>
          <span className="details-hero__meta">
            Created {formatRelative(conversation.created_at)}
          </span>
        </div>
      </div>

      {isGroup && canManage && (
        <form className="details-section" onSubmit={submitRename}>
          <label className="details-section__label" htmlFor="group-name">
            Group name
          </label>
          <div className="details-inline">
            <input
              id="group-name"
              className="text-input"
              value={name}
              onChange={(event) => setName(event.target.value)}
              maxLength={120}
              placeholder="Group name"
            />
            <button
              type="submit"
              className="button button--secondary button--small"
              disabled={
                renaming || !name.trim() || name.trim() === conversation.name
              }
            >
              {renaming ? "Saving…" : "Save"}
            </button>
          </div>
        </form>
      )}

      <div className="details-section">
        <div className="details-section__head">
          <span className="details-section__label">
            Members <span className="count-pill">{members.length}</span>
          </span>
          {isGroup && canManage && (
            <button
              type="button"
              className="button button--ghost button--small"
              onClick={() => {
                setShowAdd((value) => !value);
                setQuery("");
              }}
            >
              <Icon name={showAdd ? "x" : "plus"} size={15} />
              {showAdd ? "Cancel" : "Add member"}
            </button>
          )}
        </div>

        {isGroup && canManage && showAdd && (
          <div className="member-picker">
            <div className="sidebar__search member-picker__search">
              <Icon name="search" size={16} />
              <input
                value={query}
                onChange={(event) => setQuery(event.target.value)}
                placeholder="Search people to add"
                autoFocus
              />
            </div>
            {searching && (
              <div className="member-picker__status">
                <span className="spinner" /> Searching…
              </div>
            )}
            {!searching && candidates.length === 0 && (
              <div className="member-picker__status">
                {query
                  ? "Nobody new found."
                  : "Everyone is already in this group."}
              </div>
            )}
            <div className="member-picker__list">
              {candidates.map((candidate) => (
                <div key={candidate.id} className="member-picker__row">
                  <Avatar
                    name={candidate.full_name}
                    src={candidate.profile_picture_url}
                    size="sm"
                  />
                  <div>
                    <strong>{candidate.full_name}</strong>
                    <span>@{candidate.username}</span>
                  </div>
                  <button
                    type="button"
                    className="button button--secondary button--small"
                    onClick={() => void handleAdd(candidate)}
                    disabled={busyUserId === candidate.id}
                  >
                    {busyUserId === candidate.id ? "Adding…" : "Add"}
                  </button>
                </div>
              ))}
            </div>
          </div>
        )}

        <ul className="member-list">
          {members.map((member) => {
            const isSelf = member.user.id === user.id;
            const removable = isGroup && canManage && !isSelf && member.role !== "owner";
            return (
              <li key={member.user.id} className="member-list__row">
                <Avatar
                  name={member.user.full_name}
                  src={member.user.profile_picture_url}
                  size="sm"
                  online={isOnline(member.user)}
                />
                <div className="member-list__identity">
                  <strong>
                    {member.user.full_name}
                    {isSelf && <span className="you-pill">You</span>}
                  </strong>
                  <span>@{member.user.username}</span>
                </div>
                {isGroup && (
                  <span className={`role-pill role-pill--${member.role}`}>
                    {roleLabel(member.role)}
                  </span>
                )}
                {removable ? (
                  <button
                    type="button"
                    className="icon-button icon-button--danger"
                    title={`Remove ${member.user.full_name}`}
                    aria-label={`Remove ${member.user.full_name}`}
                    onClick={() => void handleRemove(member)}
                    disabled={busyUserId === member.user.id}
                  >
                    {busyUserId === member.user.id ? (
                      <span className="spinner" />
                    ) : (
                      <Icon name="x" size={16} />
                    )}
                  </button>
                ) : (
                  <span className="member-list__spacer" />
                )}
              </li>
            );
          })}
        </ul>
      </div>

      <div className="details-section details-section--danger">
        <div>
          <strong>Leave conversation</strong>
          <p>
            {isGroup
              ? "You will stop receiving messages and notifications from this group."
              : "The conversation will disappear from your list. The other person keeps the history."}
          </p>
        </div>
        <button
          type="button"
          className="button button--danger button--small"
          onClick={() => {
            const member = members.find((item) => item.user.id === user.id);
            if (member) void handleRemove(member);
          }}
          disabled={leaving}
        >
          {leaving ? "Leaving…" : "Leave"}
        </button>
      </div>

      {isGroup && mine?.role === "owner" && (
        <p className="details-hint">
          <Icon name="info" size={14} /> You are the owner of this group. If you
          leave, the remaining admins keep managing it.
        </p>
      )}

      <div className="details-actions">
        <button type="button" className="button button--ghost" onClick={onClose}>
          Done
        </button>
        {!isGroup && other && (
          <button
            type="button"
            className="button button--secondary"
            onClick={() => {
              void navigator.clipboard?.writeText(`@${other.user.username}`);
              toast("Username copied", "success");
            }}
          >
            Copy username
          </button>
        )}
      </div>
    </Modal>
  );
}
