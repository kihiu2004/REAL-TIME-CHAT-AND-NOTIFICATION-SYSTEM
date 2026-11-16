import type {
  AuthResponse,
  Conversation,
  ConversationListItem,
  CreateConversationInput,
  LoginInput,
  Message,
  MessagePage,
  Notification,
  NotificationPage,
  ProfileInput,
  ReadState,
  RegisterInput,
  User,
} from "./types";

const API_BASE = (import.meta.env.VITE_API_URL || "/api/v1").replace(/\/$/, "");

let authToken: string | null = null;

export function setAuthToken(token: string | null): void {
  authToken = token;
}

export class ApiError extends Error {
  status: number;
  code: string;

  constructor(message: string, status: number, code = "error") {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.code = code;
  }
}

function validationMessage(detail: unknown): string {
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail)) {
    return detail
      .map((item) => {
        if (item && typeof item === "object" && "msg" in item) {
          const msg = String((item as { msg: unknown }).msg);
          return msg.replace(/^Value error,\s*/i, "");
        }
        return String(item);
      })
      .join(" ");
  }
  return "Something went wrong";
}

async function request<T>(
  path: string,
  init: RequestInit = {},
): Promise<T> {
  const headers = new Headers(init.headers);
  if (init.body !== undefined) headers.set("Content-Type", "application/json");
  if (authToken) headers.set("Authorization", `Bearer ${authToken}`);

  let response: Response;
  try {
    response = await fetch(`${API_BASE}${path}`, { ...init, headers });
  } catch {
    throw new ApiError(
      "Cannot reach the server. Is the ConnectHub API running?",
      0,
      "network_error",
    );
  }

  if (response.status === 401) {
    window.dispatchEvent(new Event("connecthub:unauthorized"));
  }

  if (!response.ok) {
    let message = `Request failed (${response.status})`;
    let code = "error";
    try {
      const body = await response.json();
      message = validationMessage(body.detail ?? body.message ?? message);
      code = String(body.code ?? code);
    } catch {
      // Non-JSON error body (proxy/server failure).
    }
    throw new ApiError(message, response.status, code);
  }

  if (response.status === 204) return undefined as T;
  return (await response.json()) as T;
}

function query(
  params: Record<string, string | number | boolean | null | undefined>,
): string {
  const search = new URLSearchParams();
  for (const [key, value] of Object.entries(params)) {
    if (value !== undefined && value !== null && value !== "") {
      search.set(key, String(value));
    }
  }
  const text = search.toString();
  return text ? `?${text}` : "";
}

export const api = {
  register(input: RegisterInput) {
    return request<AuthResponse>("/auth/register", {
      method: "POST",
      body: JSON.stringify(input),
    });
  },

  login(input: LoginInput) {
    return request<AuthResponse>("/auth/login", {
      method: "POST",
      body: JSON.stringify(input),
    });
  },

  me() {
    return request<User>("/auth/me");
  },

  updateProfile(input: ProfileInput) {
    return request<User>("/users/me", {
      method: "PATCH",
      body: JSON.stringify(input),
    });
  },

  listUsers(search?: string) {
    return request<User[]>(`/users${query({ q: search, limit: 50 })}`);
  },

  getUser(id: string) {
    return request<User>(`/users/${id}`);
  },

  listConversations() {
    return request<ConversationListItem[]>("/conversations?limit=100");
  },

  getConversation(id: string) {
    return request<Conversation>(`/conversations/${id}`);
  },

  createConversation(input: CreateConversationInput) {
    return request<Conversation>("/conversations", {
      method: "POST",
      body: JSON.stringify(input),
    });
  },

  renameConversation(id: string, name: string) {
    return request<Conversation>(`/conversations/${id}`, {
      method: "PATCH",
      body: JSON.stringify({ name }),
    });
  },

  addMember(id: string, userId: string) {
    return request<Conversation>(`/conversations/${id}/members`, {
      method: "POST",
      body: JSON.stringify({ user_id: userId }),
    });
  },

  removeMember(id: string, userId: string) {
    return request<void>(`/conversations/${id}/members/${userId}`, {
      method: "DELETE",
    });
  },

  markRead(id: string, messageId?: string) {
    return request<ReadState>(`/conversations/${id}/read`, {
      method: "POST",
      body: JSON.stringify({ message_id: messageId ?? null }),
    });
  },

  listMessages(id: string, before?: string | null, limit = 40) {
    return request<MessagePage>(
      `/conversations/${id}/messages${query({ before, limit })}`,
    );
  },

  sendMessage(id: string, content: string, replyToId?: string | null) {
    return request<Message>(`/conversations/${id}/messages`, {
      method: "POST",
      body: JSON.stringify({
        content,
        reply_to_id: replyToId ?? null,
      }),
    });
  },

  editMessage(id: string, content: string) {
    return request<Message>(`/messages/${id}`, {
      method: "PATCH",
      body: JSON.stringify({ content }),
    });
  },

  deleteMessage(id: string) {
    return request<void>(`/messages/${id}`, { method: "DELETE" });
  },

  listNotifications(unreadOnly = false) {
    return request<NotificationPage>(
      `/notifications${query({ unread_only: unreadOnly, limit: 100 })}`,
    );
  },

  unreadNotificationCount() {
    return request<{ unread_count: number }>("/notifications/unread-count");
  },

  markNotificationRead(id: string) {
    return request<Notification>(`/notifications/${id}/read`, {
      method: "POST",
    });
  },

  markAllNotificationsRead() {
    return request<{ unread_count: number }>("/notifications/read-all", {
      method: "POST",
    });
  },
};
