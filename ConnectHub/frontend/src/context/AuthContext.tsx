import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";

import { api, setAuthToken } from "../api/client";
import type { LoginInput, RegisterInput, User } from "../api/types";

const TOKEN_KEY = "connecthub.token";

type AuthStatus = "loading" | "authenticated" | "anonymous";

interface AuthContextValue {
  user: User | null;
  token: string | null;
  status: AuthStatus;
  login: (input: LoginInput) => Promise<void>;
  register: (input: RegisterInput) => Promise<void>;
  logout: () => void;
  updateUser: (user: User) => void;
}

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [token, setToken] = useState<string | null>(null);
  const [status, setStatus] = useState<AuthStatus>("loading");

  const clearSession = useCallback(() => {
    localStorage.removeItem(TOKEN_KEY);
    setAuthToken(null);
    setToken(null);
    setUser(null);
    setStatus("anonymous");
  }, []);

  useEffect(() => {
    let cancelled = false;
    const saved = localStorage.getItem(TOKEN_KEY);

    if (!saved) {
      setStatus("anonymous");
      return;
    }

    setAuthToken(saved);
    api
      .me()
      .then((current) => {
        if (cancelled) return;
        setUser(current);
        setToken(saved);
        setStatus("authenticated");
      })
      .catch(() => {
        if (!cancelled) clearSession();
      });

    return () => {
      cancelled = true;
    };
  }, [clearSession]);

  useEffect(() => {
    const onUnauthorized = () => clearSession();
    window.addEventListener("connecthub:unauthorized", onUnauthorized);
    return () =>
      window.removeEventListener("connecthub:unauthorized", onUnauthorized);
  }, [clearSession]);

  const acceptSession = useCallback(
    (accessToken: string, current: User) => {
      localStorage.setItem(TOKEN_KEY, accessToken);
      setAuthToken(accessToken);
      setToken(accessToken);
      setUser(current);
      setStatus("authenticated");
    },
    [],
  );

  const login = useCallback(
    async (input: LoginInput) => {
      const result = await api.login(input);
      acceptSession(result.access_token, result.user);
    },
    [acceptSession],
  );

  const register = useCallback(
    async (input: RegisterInput) => {
      const result = await api.register(input);
      acceptSession(result.access_token, result.user);
    },
    [acceptSession],
  );

  const logout = useCallback(() => {
    clearSession();
  }, [clearSession]);

  const updateUser = useCallback((next: User) => {
    setUser(next);
  }, []);

  const value = useMemo<AuthContextValue>(
    () => ({ user, token, status, login, register, logout, updateUser }),
    [user, token, status, login, register, logout, updateUser],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthContextValue {
  const value = useContext(AuthContext);
  if (!value) throw new Error("useAuth must be used inside <AuthProvider>");
  return value;
}
