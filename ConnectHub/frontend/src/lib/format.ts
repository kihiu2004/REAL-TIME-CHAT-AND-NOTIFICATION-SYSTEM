import type { Conversation, Member, Message, User } from "../api/types";

export function classNames(
  ...values: Array<string | false | null | undefined>
): string {
  return values.filter(Boolean).join(" ");
}

export function initials(name: string): string {
  const parts = name.trim().split(/\s+/).filter(Boolean);
  if (parts.length === 0) return "?";
  if (parts.length === 1) return parts[0].slice(0, 2).toUpperCase();
  return `${parts[0][0]}${parts[parts.length - 1][0]}`.toUpperCase();
}

export function otherMember(
  conversation: Conversation,
  currentUserId: string,
): Member | undefined {
  return conversation.members.find((member) => member.user.id !== currentUserId);
}

export function conversationTitle(
  conversation: Conversation,
  currentUserId: string,
): string {
  if (conversation.type === "group") {
    return conversation.name?.trim() || "Untitled group";
  }
  const other = otherMember(conversation, currentUserId);
  return other?.user.full_name || other?.user.username || "Direct message";
}

export function conversationSubtitle(
  conversation: Conversation,
  currentUserId: string,
): string {
  if (conversation.type === "group") {
    const count = conversation.members.length;
    return `${count} member${count === 1 ? "" : "s"}`;
  }
  return `@${otherMember(conversation, currentUserId)?.user.username ?? "unknown"}`;
}

export function messagePreview(message: Message | null | undefined): string {
  if (!message) return "No messages yet";
  if (message.content) return message.content;
  switch (message.message_type) {
    case "image":
      return "Photo";
    case "file":
      return "File";
    case "system":
      return "System message";
    default:
      return "Message";
  }
}

export function roleLabel(role: Member["role"]): string {
  if (role === "owner") return "Owner";
  if (role === "admin") return "Admin";
  return "Member";
}

export function formatClock(value: string): string {
  return new Date(value).toLocaleTimeString([], {
    hour: "2-digit",
    minute: "2-digit",
  });
}

export function formatDay(value: string): string {
  const date = new Date(value);
  const today = new Date();
  const yesterday = new Date();
  yesterday.setDate(today.getDate() - 1);

  if (isSameDay(date, today)) return "Today";
  if (isSameDay(date, yesterday)) return "Yesterday";

  return date.toLocaleDateString([], {
    weekday: "short",
    month: "short",
    day: "numeric",
    year: date.getFullYear() === today.getFullYear() ? undefined : "numeric",
  });
}

export function formatRelative(value: string): string {
  const date = new Date(value);
  const seconds = Math.round((Date.now() - date.getTime()) / 1000);

  if (seconds < 45) return "just now";
  if (seconds < 3600) return `${Math.round(seconds / 60)}m ago`;
  if (seconds < 86400) return `${Math.round(seconds / 3600)}h ago`;
  if (seconds < 604800) return `${Math.round(seconds / 86400)}d ago`;

  return date.toLocaleDateString([], { month: "short", day: "numeric" });
}

export function formatListTime(value: string | null): string {
  if (!value) return "";
  const date = new Date(value);
  const now = new Date();
  if (isSameDay(date, now)) return formatClock(value);
  if (now.getTime() - date.getTime() < 6 * 86400000) {
    return date.toLocaleDateString([], { weekday: "short" });
  }
  return date.toLocaleDateString([], { month: "short", day: "numeric" });
}

export function formatLastSeen(value: string | null): string {
  if (!value) return "Offline";
  return `Last seen ${formatRelative(value)}`;
}

export function isSameDay(a: Date, b: Date): boolean {
  return (
    a.getFullYear() === b.getFullYear() &&
    a.getMonth() === b.getMonth() &&
    a.getDate() === b.getDate()
  );
}

export function isSameGroupDay(a: string, b: string): boolean {
  return isSameDay(new Date(a), new Date(b));
}

export function clamp(value: number, min: number, max: number): number {
  return Math.min(max, Math.max(min, value));
}
