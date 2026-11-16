import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useRef,
  useState,
  type ReactNode,
} from "react";

import { api, ApiError } from "../api/client";
import type {
  Conversation,
  ConversationListItem,
  CreateConversationInput,
  Message,
  MessagePreview,
  Notification,
  ReadEventData,
  ServerEvent,
  TypingEventData,
} from "../api/types";
import { useAuth } from "./AuthContext";
import { useToast } from "./ToastContext";
import { useWebSocket, type ConnectionState } from "../hooks/useWebSocket";

interface Pager {
  hasMore: boolean;
  nextBefore: string | null;
}

interface ChatContextValue {
  conversations: ConversationListItem[];
  activeId: string | null;
  activeConversation: ConversationListItem | null;
  messages: Message[];
  typingUsers: string[];
  loadingMessages: boolean;
  loadingMore: boolean;
  hasMoreMessages: boolean;
  notifications: Notification[];
  unreadNotifications: number;
  notificationsOpen: boolean;
  connectionState: ConnectionState;
  presence: Record<string, boolean>;
  isOnline: (user: ConversationListItem["members"][number]["user"]) => boolean;
  selectConversation: (id: string | null) => Promise<void>;
  refreshConversations: (quiet?: boolean) => Promise<void>;
  loadOlderMessages: () => Promise<void>;
  sendMessage: (content: string, replyToId?: string | null) => Promise<boolean>;
  editMessage: (messageId: string, content: string) => Promise<boolean>;
  deleteMessage: (messageId: string) => Promise<void>;
  markRead: (conversationId?: string) => Promise<void>;
  setTyping: (isTyping: boolean) => void;
  createConversation: (input: CreateConversationInput) => Promise<string>;
  renameConversation: (conversationId: string, name: string) => Promise<void>;
  addMember: (conversationId: string, userId: string) => Promise<void>;
  removeMember: (conversationId: string, userId: string) => Promise<void>;
  refreshNotifications: (quiet?: boolean) => Promise<void>;
  openNotifications: () => void;
  closeNotifications: () => void;
  markNotificationRead: (notificationId: string) => Promise<void>;
  markAllNotificationsRead: () => Promise<void>;
}

const ChatContext = createContext<ChatContextValue | null>(null);

function sortConversations(
  items: ConversationListItem[],
): ConversationListItem[] {
  return [...items].sort(
    (a, b) => new Date(b.updated_at).getTime() - new Date(a.updated_at).getTime(),
  );
}

function previewOf(message: Message): MessagePreview {
  return {
    id: message.id,
    content: message.content,
    sender_id: message.sender?.id ?? null,
    created_at: message.created_at,
  };
}

function mergeMessage(list: Message[], message: Message): Message[] {
  const index = list.findIndex((item) => item.id === message.id);
  const next = index >= 0 ? list.map((item) => (item.id === message.id ? message : item)) : [...list, message];
  return next.sort((a, b) => {
    const delta = new Date(a.created_at).getTime() - new Date(b.created_at).getTime();
    return delta !== 0 ? delta : a.id.localeCompare(b.id);
  });
}

function mergeMany(existing: Message[], incoming: Message[]): Message[] {
  const map = new Map(existing.map((message) => [message.id, message]));
  for (const message of incoming) map.set(message.id, message);
  return [...map.values()].sort((a, b) => {
    const delta = new Date(a.created_at).getTime() - new Date(b.created_at).getTime();
    return delta !== 0 ? delta : a.id.localeCompare(b.id);
  });
}

function mergeConversation(
  existing: ConversationListItem | undefined,
  conversation: Conversation,
): ConversationListItem {
  return {
    ...conversation,
    last_message: existing?.last_message ?? null,
    unread_count: existing?.unread_count ?? 0,
  };
}

export function ChatProvider({ children }: { children: ReactNode }) {
  const { user } = useAuth();
  const { toast } = useToast();
  const currentUserId = user?.id ?? "";

  const [conversations, setConversations] = useState<ConversationListItem[]>([]);
  const [activeId, setActiveId] = useState<string | null>(null);
  const activeIdRef = useRef<string | null>(null);
  const [messagesByConversation, setMessagesByConversation] = useState<
    Record<string, Message[]>
  >({});
  const messagesByConversationRef = useRef(messagesByConversation);
  messagesByConversationRef.current = messagesByConversation;

  const [pagers, setPagers] = useState<Record<string, Pager>>({});
  const pagersRef = useRef(pagers);
  pagersRef.current = pagers;

  const [loadingMessages, setLoadingMessages] = useState(false);
  const [loadingMore, setLoadingMore] = useState(false);
  const [typingByConversation, setTypingByConversation] = useState<
    Record<string, Record<string, string>>
  >({});
  const [notifications, setNotifications] = useState<Notification[]>([]);
  const notificationsRef = useRef(notifications);
  notificationsRef.current = notifications;
  const [unreadNotifications, setUnreadNotifications] = useState(0);
  const [notificationsOpen, setNotificationsOpen] = useState(false);
  const [presence, setPresence] = useState<Record<string, boolean>>({});

  const loadRequestRef = useRef(0);
  const readTimers = useRef(new Map<string, number>());
  const typingTimers = useRef(new Map<string, number>());
  const refreshRef = useRef<(quiet?: boolean) => Promise<void>>(async () => {});

  const handleError = useCallback(
    (error: unknown, fallback = "Something went wrong") => {
      if (error instanceof ApiError && error.status === 401) return;
      toast(error instanceof Error ? error.message : fallback, "error");
    },
    [toast],
  );

  const refreshConversations = useCallback(
    async (quiet = false) => {
      try {
        const items = await api.listConversations();
        setConversations(sortConversations(items));
        setPresence((previous) => {
          const next = { ...previous };
          for (const conversation of items) {
            for (const member of conversation.members) {
              next[member.user.id] = member.user.is_online;
            }
          }
          return next;
        });
      } catch (error) {
        if (!quiet) handleError(error, "Could not load conversations");
      }
    },
    [handleError],
  );
  refreshRef.current = refreshConversations;

  const refreshNotifications = useCallback(
    async (quiet = false) => {
      try {
        const page = await api.listNotifications();
        setNotifications(page.items);
        setUnreadNotifications(page.unread_count);
      } catch (error) {
        if (!quiet) handleError(error, "Could not load notifications");
      }
    },
    [handleError],
  );

  useEffect(() => {
    void refreshConversations();
    void refreshNotifications();
  }, [refreshConversations, refreshNotifications]);

  useEffect(() => {
    const onFocus = () => void refreshConversations(true);
    const timer = window.setInterval(() => {
      if (document.visibilityState === "visible") void refreshConversations(true);
    }, 45_000);
    window.addEventListener("focus", onFocus);
    return () => {
      window.clearInterval(timer);
      window.removeEventListener("focus", onFocus);
    };
  }, [refreshConversations]);

  useEffect(() => {
    return () => {
      readTimers.current.forEach((timer) => window.clearTimeout(timer));
      typingTimers.current.forEach((timer) => window.clearTimeout(timer));
      readTimers.current.clear();
      typingTimers.current.clear();
    };
  }, []);

  const patchReadState = useCallback(
    (conversationId: string, userId: string, lastReadAt: string) => {
      setConversations((previous) =>
        previous.map((conversation) =>
          conversation.id === conversationId
            ? {
                ...conversation,
                members: conversation.members.map((member) =>
                  member.user.id === userId
                    ? { ...member, last_read_at: lastReadAt }
                    : member,
                ),
              }
            : conversation,
        ),
      );
    },
    [],
  );

  const markRead = useCallback(
    async (conversationId?: string) => {
      const id = conversationId ?? activeIdRef.current;
      if (!id) return;
      try {
        const state = await api.markRead(id);
        patchReadState(id, currentUserId, state.last_read_at);
        setConversations((previous) =>
          previous.map((conversation) =>
            conversation.id === id
              ? { ...conversation, unread_count: 0 }
              : conversation,
          ),
        );
      } catch (error) {
        handleError(error, "Could not mark the conversation as read");
      }
    },
    [currentUserId, handleError, patchReadState],
  );

  const scheduleRead = useCallback(
    (conversationId: string, messageId?: string) => {
      const existing = readTimers.current.get(conversationId);
      if (existing) window.clearTimeout(existing);

      const timer = window.setTimeout(async () => {
        readTimers.current.delete(conversationId);
        if (activeIdRef.current !== conversationId) return;
        try {
          const state = await api.markRead(conversationId, messageId);
          patchReadState(conversationId, currentUserId, state.last_read_at);
          setConversations((previous) =>
            previous.map((conversation) =>
              conversation.id === conversationId
                ? { ...conversation, unread_count: 0 }
                : conversation,
            ),
          );
        } catch {
          // A failed read receipt is not worth interrupting the conversation.
        }
      }, 700);
      readTimers.current.set(conversationId, timer);
    },
    [currentUserId, patchReadState],
  );

  const selectConversation = useCallback(
    async (id: string | null) => {
      setActiveId(id);
      activeIdRef.current = id;
      setLoadingMessages(Boolean(id));

      if (!id) return;

      const cached = messagesByConversationRef.current[id];
      if (cached && cached.length > 0) {
        setLoadingMessages(false);
        setConversations((previous) =>
          previous.map((conversation) =>
            conversation.id === id
              ? { ...conversation, unread_count: 0 }
              : conversation,
          ),
        );
        void markRead(id);
        return;
      }

      const requestId = ++loadRequestRef.current;
      try {
        const [conversation, page] = await Promise.all([
          api.getConversation(id),
          api.listMessages(id),
        ]);
        if (loadRequestRef.current !== requestId) return;

        setConversations((previous) => {
          const existing = previous.find((item) => item.id === id);
          if (!existing) {
            return sortConversations([
              ...previous,
              mergeConversation(undefined, conversation),
            ]);
          }
          return previous.map((item) =>
            item.id === id
              ? { ...item, ...conversation, unread_count: 0 }
              : item,
          );
        });

        setMessagesByConversation((previous) => ({
          ...previous,
          [id]: [...page.items].reverse(),
        }));
        setPagers((previous) => ({
          ...previous,
          [id]: { hasMore: page.has_more, nextBefore: page.next_before },
        }));
        void markRead(id);
      } catch (error) {
        handleError(error, "Could not open that conversation");
      } finally {
        if (loadRequestRef.current === requestId) setLoadingMessages(false);
      }
    },
    [handleError, markRead],
  );

  const loadOlderMessages = useCallback(async () => {
    const id = activeIdRef.current;
    if (!id || loadingMore) return;
    const pager = pagersRef.current[id];
    if (!pager?.hasMore || !pager.nextBefore) return;

    setLoadingMore(true);
    try {
      const page = await api.listMessages(id, pager.nextBefore);
      setMessagesByConversation((previous) => ({
        ...previous,
        [id]: mergeMany(previous[id] ?? [], [...page.items].reverse()),
      }));
      setPagers((previous) => ({
        ...previous,
        [id]: { hasMore: page.has_more, nextBefore: page.next_before },
      }));
    } catch (error) {
      handleError(error, "Could not load older messages");
    } finally {
      setLoadingMore(false);
    }
  }, [handleError, loadingMore]);

  const sendMessage = useCallback(
    async (content: string, replyToId?: string | null): Promise<boolean> => {
      const id = activeIdRef.current;
      const trimmed = content.trim();
      if (!id || !trimmed) return false;

      try {
        const message = await api.sendMessage(id, trimmed, replyToId);
        setMessagesByConversation((previous) => ({
          ...previous,
          [id]: mergeMessage(previous[id] ?? [], message),
        }));
        setConversations((previous) =>
          previous.map((conversation) =>
            conversation.id === id
              ? {
                  ...conversation,
                  last_message: previewOf(message),
                  updated_at: message.created_at,
                  unread_count: 0,
                }
              : conversation,
          ),
        );
        return true;
      } catch (error) {
        handleError(error, "Message could not be sent");
        return false;
      }
    },
    [handleError],
  );

  const editMessage = useCallback(
    async (messageId: string, content: string): Promise<boolean> => {
      const id = activeIdRef.current;
      const trimmed = content.trim();
      if (!id || !trimmed) return false;

      try {
        const message = await api.editMessage(messageId, trimmed);
        setMessagesByConversation((previous) => ({
          ...previous,
          [id]: mergeMessage(previous[id] ?? [], message),
        }));
        setConversations((previous) =>
          previous.map((conversation) =>
            conversation.id === id &&
            conversation.last_message?.id === message.id
              ? { ...conversation, last_message: previewOf(message) }
              : conversation,
          ),
        );
        return true;
      } catch (error) {
        handleError(error, "Message could not be edited");
        return false;
      }
    },
    [handleError],
  );

  const deleteMessage = useCallback(
    async (messageId: string) => {
      const id = activeIdRef.current;
      if (!id) return;

      try {
        await api.deleteMessage(messageId);
        setMessagesByConversation((previous) => ({
          ...previous,
          [id]: (previous[id] ?? []).filter((message) => message.id !== messageId),
        }));
        setConversations((previous) =>
          previous.map((conversation) =>
            conversation.id === id && conversation.last_message?.id === messageId
              ? { ...conversation, last_message: null }
              : conversation,
          ),
        );
        void refreshConversations(true);
      } catch (error) {
        handleError(error, "Message could not be deleted");
      }
    },
    [handleError, refreshConversations],
  );

  const createConversation = useCallback(
    async (input: CreateConversationInput): Promise<string> => {
      const conversation = await api.createConversation(input);
      await refreshConversations(true);
      await selectConversation(conversation.id);
      return conversation.id;
    },
    [refreshConversations, selectConversation],
  );

  const renameConversation = useCallback(
    async (conversationId: string, name: string) => {
      try {
        const updated = await api.renameConversation(conversationId, name.trim());
        setConversations((previous) =>
          previous.map((conversation) =>
            conversation.id === conversationId
              ? { ...conversation, name: updated.name, updated_at: updated.updated_at }
              : conversation,
          ),
        );
        toast("Group renamed", "success");
      } catch (error) {
        handleError(error, "Could not rename the group");
        throw error;
      }
    },
    [handleError, toast],
  );

  const addMember = useCallback(
    async (conversationId: string, userId: string) => {
      try {
        const updated = await api.addMember(conversationId, userId);
        setConversations((previous) =>
          previous.map((conversation) =>
            conversation.id === conversationId
              ? {
                  ...conversation,
                  members: updated.members,
                  updated_at: updated.updated_at,
                }
              : conversation,
          ),
        );
        toast("Member added", "success");
      } catch (error) {
        handleError(error, "Could not add that member");
        throw error;
      }
    },
    [handleError, toast],
  );

  const removeMember = useCallback(
    async (conversationId: string, userId: string) => {
      try {
        await api.removeMember(conversationId, userId);

        if (userId === currentUserId) {
          setConversations((previous) =>
            previous.filter((conversation) => conversation.id !== conversationId),
          );
          setMessagesByConversation((previous) => {
            const next = { ...previous };
            delete next[conversationId];
            return next;
          });
          if (activeIdRef.current === conversationId) {
            activeIdRef.current = null;
            setActiveId(null);
          }
          toast("You left the conversation", "success");
          return;
        }

        const updated = await api.getConversation(conversationId);
        setConversations((previous) =>
          previous.map((conversation) =>
            conversation.id === conversationId
              ? { ...conversation, members: updated.members }
              : conversation,
          ),
        );
        toast("Member removed", "success");
      } catch (error) {
        handleError(error, "Could not remove that member");
        throw error;
      }
    },
    [currentUserId, handleError, toast],
  );

  const setTyping = useCallback(
    (isTyping: boolean) => {
      const id = activeIdRef.current;
      if (!id) return;
      send(isTyping ? "typing.start" : "typing.stop", { conversation_id: id });
    },
    // `send` is stable for the lifetime of the hook.
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [],
  );

  const markNotificationRead = useCallback(
    async (notificationId: string) => {
      const existing = notificationsRef.current.find(
        (notification) => notification.id === notificationId,
      );
      try {
        const updated = await api.markNotificationRead(notificationId);
        setNotifications((previous) =>
          previous.map((notification) =>
            notification.id === notificationId ? updated : notification,
          ),
        );
        if (existing && !existing.is_read) {
          setUnreadNotifications((count) => Math.max(0, count - 1));
        }
      } catch (error) {
        handleError(error, "Could not mark the notification as read");
      }
    },
    [handleError],
  );

  const markAllNotificationsRead = useCallback(async () => {
    try {
      await api.markAllNotificationsRead();
      const now = new Date().toISOString();
      setNotifications((previous) =>
        previous.map((notification) => ({
          ...notification,
          is_read: true,
          read_at: notification.read_at ?? now,
        })),
      );
      setUnreadNotifications(0);
      toast("All notifications marked as read", "success");
    } catch (error) {
      handleError(error, "Could not update notifications");
    }
  }, [handleError, toast]);

  const onEvent = (event: ServerEvent) => {
    switch (event.type) {
      case "message.new": {
        const message = event.data as Message;
        const conversationId = message.conversation_id;
        const isActive = activeIdRef.current === conversationId;
        const own = message.sender?.id === currentUserId;

        setMessagesByConversation((previous) => ({
          ...previous,
          [conversationId]: mergeMessage(previous[conversationId] ?? [], message),
        }));

        const senderId = message.sender?.id;
        if (senderId) {
          const key = `${conversationId}:${senderId}`;
          const timer = typingTimers.current.get(key);
          if (timer) window.clearTimeout(timer);
          typingTimers.current.delete(key);
          setTypingByConversation((previous) => {
            if (!previous[conversationId]?.[senderId]) return previous;
            const nextConversation = { ...previous[conversationId] };
            delete nextConversation[senderId];
            return { ...previous, [conversationId]: nextConversation };
          });
        }

        setConversations((previous) => {
          const index = previous.findIndex(
            (conversation) => conversation.id === conversationId,
          );
          if (index < 0) {
            void refreshRef.current(true);
            return previous;
          }
          const current = previous[index];
          const updated: ConversationListItem = {
            ...current,
            last_message: previewOf(message),
            updated_at: message.created_at,
            unread_count: isActive ? 0 : own ? current.unread_count : current.unread_count + 1,
          };
          return [updated, ...previous.filter((item) => item.id !== conversationId)];
        });

        if (isActive) scheduleRead(conversationId, message.id);
        break;
      }

      case "message.updated": {
        const message = event.data as Message;
        setMessagesByConversation((previous) => ({
          ...previous,
          [message.conversation_id]: mergeMessage(
            previous[message.conversation_id] ?? [],
            message,
          ),
        }));
        setConversations((previous) =>
          previous.map((conversation) =>
            conversation.id === message.conversation_id &&
            conversation.last_message?.id === message.id
              ? { ...conversation, last_message: previewOf(message) }
              : conversation,
          ),
        );
        break;
      }

      case "message.deleted": {
        const data = event.data as { conversation_id: string; message_id: string };
        setMessagesByConversation((previous) => ({
          ...previous,
          [data.conversation_id]: (previous[data.conversation_id] ?? []).filter(
            (message) => message.id !== data.message_id,
          ),
        }));
        setConversations((previous) =>
          previous.map((conversation) =>
            conversation.id === data.conversation_id &&
            conversation.last_message?.id === data.message_id
              ? { ...conversation, last_message: null }
              : conversation,
          ),
        );
        break;
      }

      case "typing": {
        const data = event.data as TypingEventData;
        if (data.user_id === currentUserId) break;
        const key = `${data.conversation_id}:${data.user_id}`;
        const previousTimer = typingTimers.current.get(key);
        if (previousTimer) window.clearTimeout(previousTimer);

        if (!data.is_typing) {
          typingTimers.current.delete(key);
          setTypingByConversation((previous) => {
            if (!previous[data.conversation_id]?.[data.user_id]) return previous;
            const nextConversation = { ...previous[data.conversation_id] };
            delete nextConversation[data.user_id];
            return { ...previous, [data.conversation_id]: nextConversation };
          });
          break;
        }

        typingTimers.current.set(
          key,
          window.setTimeout(() => {
            typingTimers.current.delete(key);
            setTypingByConversation((previous) => {
              if (!previous[data.conversation_id]?.[data.user_id]) return previous;
              const nextConversation = { ...previous[data.conversation_id] };
              delete nextConversation[data.user_id];
              return { ...previous, [data.conversation_id]: nextConversation };
            });
          }, 6500),
        );
        setTypingByConversation((previous) => ({
          ...previous,
          [data.conversation_id]: {
            ...(previous[data.conversation_id] ?? {}),
            [data.user_id]: data.username,
          },
        }));
        break;
      }

      case "message.read": {
        const data = event.data as ReadEventData;
        patchReadState(data.conversation_id, data.user_id, data.last_read_at);
        break;
      }

      case "notification.new": {
        const notification = event.data as Notification;
        setNotifications((previous) => [
          notification,
          ...previous.filter((item) => item.id !== notification.id),
        ]);
        setUnreadNotifications((count) => count + 1);
        toast(notification.title, "info");
        break;
      }

      case "error": {
        const data = event.data as { detail?: string };
        toast(data?.detail ?? "Realtime error", "error");
        break;
      }

      default:
        break;
    }
  };

  const { state: connectionState, send } = useWebSocket({
    token: localStorage.getItem("connecthub.token"),
    onEvent,
  });

  const activeConversation =
    conversations.find((conversation) => conversation.id === activeId) ?? null;
  const messages = activeId ? messagesByConversation[activeId] ?? [] : [];
  const typingUsers = activeId
    ? Object.values(typingByConversation[activeId] ?? {})
    : [];
  const hasMoreMessages = activeId
    ? pagers[activeId]?.hasMore ?? false
    : false;

  const isOnline = useCallback(
    (member: ConversationListItem["members"][number]["user"]) =>
      presence[member.id] ?? member.is_online,
    [presence],
  );

  const value = useMemo<ChatContextValue>(
    () => ({
      conversations,
      activeId,
      activeConversation,
      messages,
      typingUsers,
      loadingMessages,
      loadingMore,
      hasMoreMessages,
      notifications,
      unreadNotifications,
      notificationsOpen,
      connectionState,
      presence,
      isOnline,
      selectConversation,
      refreshConversations,
      loadOlderMessages,
      sendMessage,
      editMessage,
      deleteMessage,
      markRead,
      setTyping,
      createConversation,
      renameConversation,
      addMember,
      removeMember,
      refreshNotifications,
      openNotifications: () => {
        setNotificationsOpen(true);
        void refreshNotifications(true);
      },
      closeNotifications: () => setNotificationsOpen(false),
      markNotificationRead,
      markAllNotificationsRead,
    }),
    [
      conversations,
      activeId,
      activeConversation,
      messages,
      typingUsers,
      loadingMessages,
      loadingMore,
      hasMoreMessages,
      notifications,
      unreadNotifications,
      notificationsOpen,
      connectionState,
      presence,
      isOnline,
      selectConversation,
      refreshConversations,
      loadOlderMessages,
      sendMessage,
      editMessage,
      deleteMessage,
      markRead,
      setTyping,
      createConversation,
      renameConversation,
      addMember,
      removeMember,
      refreshNotifications,
      markNotificationRead,
      markAllNotificationsRead,
    ],
  );

  return <ChatContext.Provider value={value}>{children}</ChatContext.Provider>;
}

export function useChat(): ChatContextValue {
  const value = useContext(ChatContext);
  if (!value) throw new Error("useChat must be used inside <ChatProvider>");
  return value;
}
