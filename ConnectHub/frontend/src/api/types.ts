// Shapes returned by the FastAPI schema layer (app/schemas/*.py).

export type UserStatus = "active" | "inactive" | "suspended";
export type MemberRole = "owner" | "admin" | "member";
export type ConversationType = "direct" | "group";
export type MessageType = "text" | "image" | "file" | "system";
export type NotificationType =
  | "message"
  | "mention"
  | "conversation_invite"
  | "system";

export interface User {
  id: string;
  username: string;
  email: string;
  full_name: string;
  profile_picture_url: string | null;
  account_status: UserStatus;
  is_online: boolean;
  last_seen_at: string | null;
  created_at: string;
}

export interface Member {
  user: User;
  role: MemberRole;
  joined_at: string;
  last_read_at: string | null;
}

export interface Conversation {
  id: string;
  type: ConversationType;
  name: string | null;
  created_by: string | null;
  created_at: string;
  updated_at: string;
  members: Member[];
}

export interface MessagePreview {
  id: string;
  content: string | null;
  sender_id: string | null;
  created_at: string;
}

export interface ConversationListItem extends Conversation {
  last_message: MessagePreview | null;
  unread_count: number;
}

export interface Message {
  id: string;
  conversation_id: string;
  sender: User | null;
  content: string | null;
  message_type: MessageType;
  reply_to_id: string | null;
  is_edited: boolean;
  edited_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface MessagePage {
  items: Message[];
  has_more: boolean;
  next_before: string | null;
}

export interface Notification {
  id: string;
  type: NotificationType;
  title: string;
  body: string | null;
  data: Record<string, unknown> | null;
  is_read: boolean;
  read_at: string | null;
  created_at: string;
}

export interface NotificationPage {
  items: Notification[];
  unread_count: number;
}

export interface AuthResponse {
  access_token: string;
  token_type: string;
  user: User;
}

export interface ReadState {
  last_read_at: string;
}

export interface RegisterInput {
  username: string;
  email: string;
  full_name: string;
  password: string;
}

export interface LoginInput {
  identifier: string;
  password: string;
}

export interface ProfileInput {
  full_name?: string;
  email?: string;
  profile_picture_url?: string | null;
}

export interface CreateConversationInput {
  type: ConversationType;
  name?: string | null;
  member_ids: string[];
}

/** One frame delivered by the server over the /ws channel. */
export interface ServerEvent<T = unknown> {
  type: string;
  data: T;
}

export interface TypingEventData {
  conversation_id: string;
  user_id: string;
  username: string;
  is_typing: boolean;
}

export interface ReadEventData {
  conversation_id: string;
  user_id: string;
  last_read_at: string;
}
