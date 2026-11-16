import { useState, type FormEvent } from "react";

import { ApiError } from "../api/client";
import { useAuth } from "../context/AuthContext";
import { useToast } from "../context/ToastContext";
import { Icon } from "./Icons";

type Mode = "login" | "register";

interface FormState {
  identifier: string;
  username: string;
  email: string;
  fullName: string;
  password: string;
}

const EMPTY_FORM: FormState = {
  identifier: "",
  username: "",
  email: "",
  fullName: "",
  password: "",
};

export function AuthPage() {
  const { login, register } = useAuth();
  const { toast } = useToast();
  const [mode, setMode] = useState<Mode>("login");
  const [form, setForm] = useState<FormState>(EMPTY_FORM);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [showPassword, setShowPassword] = useState(false);

  const switchMode = (next: Mode) => {
    setMode(next);
    setError(null);
    setForm(EMPTY_FORM);
  };

  const update = (field: keyof FormState, value: string) => {
    setForm((current) => ({ ...current, [field]: value }));
  };

  const submit = async (event: FormEvent) => {
    event.preventDefault();
    if (busy) return;
    setError(null);

    if (mode === "login") {
      if (!form.identifier.trim() || !form.password) {
        setError("Enter your username or email and your password.");
        return;
      }
    } else {
      if (!/^[A-Za-z0-9_.-]{3,50}$/.test(form.username.trim())) {
        setError(
          "Usernames need 3-50 characters (letters, numbers, dot, dash or underscore).",
        );
        return;
      }
      if (!form.fullName.trim()) {
        setError("Please enter your full name.");
        return;
      }
      if (form.password.length < 8) {
        setError("Passwords need at least 8 characters.");
        return;
      }
    }

    setBusy(true);
    try {
      if (mode === "login") {
        await login({
          identifier: form.identifier.trim(),
          password: form.password,
        });
        toast("Welcome back!", "success");
      } else {
        await register({
          username: form.username.trim().toLowerCase(),
          email: form.email.trim(),
          full_name: form.fullName.trim(),
          password: form.password,
        });
        toast("Account created. Welcome to ConnectHub!", "success");
      }
    } catch (caught) {
      setError(
        caught instanceof ApiError
          ? caught.message
          : "Something went wrong. Please try again.",
      );
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="auth-page">
      <div className="auth-orb auth-orb--one" aria-hidden="true" />
      <div className="auth-orb auth-orb--two" aria-hidden="true" />

      <div className="auth-card">
        <aside className="auth-hero">
          <div className="brand brand--large">
            <span className="brand__mark">
              <Icon name="chat" size={22} />
            </span>
            <span className="brand__name">ConnectHub</span>
          </div>

          <h1>Conversations that feel alive.</h1>
          <p className="auth-hero__lead">
            Realtime messages, typing indicators, read receipts and instant
            notifications — in one focused workspace.
          </p>

          <ul className="auth-features">
            <li>
              <span className="auth-features__icon">
                <Icon name="spark" size={17} />
              </span>
              <div>
                <strong>Live by default</strong>
                <span>Messages and presence update instantly over WebSocket.</span>
              </div>
            </li>
            <li>
              <span className="auth-features__icon">
                <Icon name="bell" size={17} />
              </span>
              <div>
                <strong>Nothing slips by</strong>
                <span>Unread badges and notifications follow you in real time.</span>
              </div>
            </li>
            <li>
              <span className="auth-features__icon">
                <Icon name="lock" size={17} />
              </span>
              <div>
                <strong>Private by design</strong>
                <span>JWT sessions and hashed passwords protect every account.</span>
              </div>
            </li>
          </ul>

          <div className="auth-hero__footer">
            <span className="status-pill">
              <span className="status-pill__dot" />
              FastAPI · MySQL · Redis · WebSockets
            </span>
          </div>
        </aside>

        <section className="auth-panel">
          <div className="auth-tabs" role="tablist" aria-label="Account access">
            <button
              type="button"
              role="tab"
              aria-selected={mode === "login"}
              className={mode === "login" ? "is-active" : ""}
              onClick={() => switchMode("login")}
            >
              Sign in
            </button>
            <button
              type="button"
              role="tab"
              aria-selected={mode === "register"}
              className={mode === "register" ? "is-active" : ""}
              onClick={() => switchMode("register")}
            >
              Create account
            </button>
          </div>

          <div className="auth-panel__heading">
            <h2>{mode === "login" ? "Welcome back" : "Get started"}</h2>
            <p>
              {mode === "login"
                ? "Sign in to pick up your conversations."
                : "Create an account and start chatting in seconds."}
            </p>
          </div>

          {error && (
            <div className="form-error" role="alert">
              <Icon name="warning" size={16} />
              <span>{error}</span>
            </div>
          )}

          <form className="auth-form" onSubmit={submit} noValidate>
            {mode === "register" ? (
              <>
                <label className="field">
                  <span className="field__label">Full name</span>
                  <span className="field__control">
                    <Icon name="user" size={17} />
                    <input
                      value={form.fullName}
                      onChange={(event) => update("fullName", event.target.value)}
                      placeholder="Ada Lovelace"
                      autoComplete="name"
                      maxLength={120}
                      autoFocus
                    />
                  </span>
                </label>

                <div className="field-row">
                  <label className="field">
                    <span className="field__label">Username</span>
                    <span className="field__control">
                      <Icon name="at" size={17} />
                      <input
                        value={form.username}
                        onChange={(event) => update("username", event.target.value)}
                        placeholder="ada"
                        autoComplete="username"
                        maxLength={50}
                      />
                    </span>
                  </label>
                  <label className="field">
                    <span className="field__label">Email</span>
                    <span className="field__control">
                      <Icon name="mail" size={17} />
                      <input
                        value={form.email}
                        onChange={(event) => update("email", event.target.value)}
                        placeholder="ada@example.com"
                        type="email"
                        autoComplete="email"
                      />
                    </span>
                  </label>
                </div>
              </>
            ) : (
              <label className="field">
                <span className="field__label">Username or email</span>
                <span className="field__control">
                  <Icon name="at" size={17} />
                  <input
                    value={form.identifier}
                    onChange={(event) => update("identifier", event.target.value)}
                    placeholder="ada or ada@example.com"
                    autoComplete="username"
                    autoFocus
                  />
                </span>
              </label>
            )}

            <label className="field">
              <span className="field__label">Password</span>
              <span className="field__control">
                <Icon name="lock" size={17} />
                <input
                  value={form.password}
                  onChange={(event) => update("password", event.target.value)}
                  placeholder={
                    mode === "register" ? "At least 8 characters" : "Your password"
                  }
                  type={showPassword ? "text" : "password"}
                  autoComplete={
                    mode === "register" ? "new-password" : "current-password"
                  }
                  maxLength={72}
                />
                <button
                  type="button"
                  className="field__toggle"
                  onClick={() => setShowPassword((value) => !value)}
                >
                  {showPassword ? "Hide" : "Show"}
                </button>
              </span>
            </label>

            <button
              type="submit"
              className="button button--primary button--block"
              disabled={busy}
            >
              {busy ? (
                <>
                  <span className="spinner" /> Please wait…
                </>
              ) : mode === "login" ? (
                "Sign in"
              ) : (
                "Create account"
              )}
            </button>
          </form>

          <p className="auth-panel__note">
            {mode === "login" ? (
              <>
                New to ConnectHub?{" "}
                <button type="button" className="link" onClick={() => switchMode("register")}>
                  Create an account
                </button>
              </>
            ) : (
              <>
                Already have an account?{" "}
                <button type="button" className="link" onClick={() => switchMode("login")}>
                  Sign in
                </button>
              </>
            )}
          </p>
        </section>
      </div>
    </div>
  );
}
