import { useCallback, useEffect, useRef, useState } from "react";

import type { ServerEvent } from "../api/types";

export type ConnectionState = "connecting" | "open" | "closed";

function websocketUrl(token: string): string {
  const configured = import.meta.env.VITE_WS_URL;
  const base =
    configured ||
    `${window.location.protocol === "https:" ? "wss:" : "ws:"}//${
      window.location.host
    }/ws`;
  return `${base}${base.includes("?") ? "&" : "?"}token=${encodeURIComponent(
    token,
  )}`;
}

/**
 * Keeps one authenticated WebSocket open, reconnects with exponential
 * backoff, and sends a heartbeat so the server's presence TTL stays fresh.
 */
export function useWebSocket(options: {
  token: string | null;
  onEvent: (event: ServerEvent) => void;
}) {
  const { token, onEvent } = options;
  const [state, setState] = useState<ConnectionState>("closed");
  const socketRef = useRef<WebSocket | null>(null);
  const onEventRef = useRef(onEvent);
  onEventRef.current = onEvent;

  useEffect(() => {
    if (!token) {
      setState("closed");
      return;
    }

    let disposed = false;
    let attempt = 0;
    let reconnectTimer: number | undefined;
    let heartbeatTimer: number | undefined;

    const connect = () => {
      if (disposed) return;
      setState("connecting");

      const socket = new WebSocket(websocketUrl(token));
      socketRef.current = socket;

      socket.onopen = () => {
        if (disposed) return;
        attempt = 0;
        setState("open");
        heartbeatTimer = window.setInterval(() => {
          if (socket.readyState === WebSocket.OPEN) {
            socket.send(JSON.stringify({ type: "ping" }));
          }
        }, 25_000);
      };

      socket.onmessage = (event) => {
        if (typeof event.data !== "string") return;
        try {
          const parsed = JSON.parse(event.data) as ServerEvent;
          if (parsed && typeof parsed.type === "string") {
            onEventRef.current(parsed);
          }
        } catch {
          // Ignore malformed frames instead of breaking the connection.
        }
      };

      socket.onclose = (event) => {
        if (heartbeatTimer) window.clearInterval(heartbeatTimer);
        heartbeatTimer = undefined;
        if (socketRef.current === socket) socketRef.current = null;
        if (disposed) return;

        setState("closed");

        // 4401/4403 mean the token is bad or the account is disabled; retrying
        // cannot help, so surface it as a signed-out state.
        if (event.code === 4401 || event.code === 4403) {
          window.dispatchEvent(new Event("connecthub:unauthorized"));
          return;
        }

        const delay = Math.min(20_000, 800 * 2 ** attempt);
        attempt += 1;
        reconnectTimer = window.setTimeout(connect, delay);
      };

      socket.onerror = () => {
        socket.close();
      };
    };

    connect();

    return () => {
      disposed = true;
      if (reconnectTimer) window.clearTimeout(reconnectTimer);
      if (heartbeatTimer) window.clearInterval(heartbeatTimer);
      const socket = socketRef.current;
      socketRef.current = null;
      if (socket) {
        socket.onclose = null;
        socket.close();
      }
    };
  }, [token]);

  const send = useCallback((type: string, data: Record<string, unknown> = {}) => {
    const socket = socketRef.current;
    if (!socket || socket.readyState !== WebSocket.OPEN) return false;
    socket.send(JSON.stringify({ type, data }));
    return true;
  }, []);

  return { state, send };
}
