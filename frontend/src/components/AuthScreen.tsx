import { useEffect, useState } from "react";
import { login, signup, waitForBackend } from "../api";
import type { User } from "../types";
import "./AuthScreen.css";

interface Props {
  onAuthed: (user: User) => void;
}

type Mode = "login" | "signup";

export default function AuthScreen({ onAuthed }: Props) {
  const [mode, setMode] = useState<Mode>("login");
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [server, setServer] = useState<"waking" | "ready" | "down">("waking");

  // Start waking the (possibly sleeping) backend while the user types.
  useEffect(() => {
    let cancelled = false;
    waitForBackend()
      .then(() => !cancelled && setServer("ready"))
      .catch(() => !cancelled && setServer("down"));
    return () => {
      cancelled = true;
    };
  }, []);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError("");
    setBusy(true);
    try {
      const user =
        mode === "signup"
          ? await signup(email, password, name)
          : await login(email, password);
      onAuthed(user);
    } catch (err) {
      if (err instanceof TypeError) setServer("down");
      setError(
        err instanceof TypeError
          ? "Couldn't reach the server. Please try again in a minute."
          : (err as Error).message
      );
    } finally {
      setBusy(false);
    }
  }

  function switchMode(next: Mode) {
    setMode(next);
    setError("");
  }

  return (
    <div className="auth-shell">
      <div className="auth-card">
        <div className="auth-brand">
          <div className="auth-shield">🏛️</div>
          <h1 className="auth-title">Yale SOM</h1>
          <p className="auth-subtitle">Fall 2026 Course Explorer</p>
        </div>

        {server === "waking" && (
          <div className="auth-notice" role="status">
            <span className="auth-spinner" aria-hidden="true" />
            Waking up the server. The free hosting sleeps when idle, so this can take up to a minute.
          </div>
        )}
        {server === "down" && !error && (
          <div className="auth-error" role="alert">
            The server isn't responding right now. Please refresh in a minute.
          </div>
        )}

        <div className="auth-tabs" role="tablist">
          <button
            type="button"
            role="tab"
            aria-selected={mode === "login"}
            className={`auth-tab ${mode === "login" ? "active" : ""}`}
            onClick={() => switchMode("login")}
          >
            Sign in
          </button>
          <button
            type="button"
            role="tab"
            aria-selected={mode === "signup"}
            className={`auth-tab ${mode === "signup" ? "active" : ""}`}
            onClick={() => switchMode("signup")}
          >
            Create account
          </button>
        </div>

        <form className="auth-form" onSubmit={handleSubmit}>
          {mode === "signup" && (
            <label className="auth-field">
              <span>Name</span>
              <input
                type="text"
                value={name}
                onChange={(e) => setName(e.target.value)}
                placeholder="Your name"
                autoComplete="name"
              />
            </label>
          )}

          <label className="auth-field">
            <span>Email</span>
            <input
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="you@yale.edu"
              autoComplete="email"
              required
            />
          </label>

          <label className="auth-field">
            <span>Password</span>
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder={mode === "signup" ? "At least 8 characters" : "Your password"}
              autoComplete={mode === "signup" ? "new-password" : "current-password"}
              minLength={mode === "signup" ? 8 : undefined}
              maxLength={72}
              required
            />
          </label>

          {error && <div className="auth-error" role="alert">{error}</div>}

          <button type="submit" className="auth-submit" disabled={busy}>
            {busy
              ? server === "ready" ? "…" : "Connecting…"
              : mode === "signup" ? "Create account" : "Sign in"}
          </button>
        </form>

        <p className="auth-switch">
          {mode === "login" ? (
            <>
              New here?{" "}
              <button type="button" onClick={() => switchMode("signup")}>Create an account</button>
            </>
          ) : (
            <>
              Already have an account?{" "}
              <button type="button" onClick={() => switchMode("login")}>Sign in</button>
            </>
          )}
        </p>
      </div>
    </div>
  );
}
