import type { ChatMessage, Course, User } from "./types";

// Set VITE_API_URL at build time (e.g. on Render) to point at the deployed backend.
const BASE = (import.meta.env.VITE_API_URL ?? "http://localhost:8000").replace(/\/+$/, "");

const TOKEN_KEY = "som_token";

export class UnauthorizedError extends Error {}

export function getToken(): string | null {
  return localStorage.getItem(TOKEN_KEY);
}

export function setToken(token: string | null) {
  if (token) localStorage.setItem(TOKEN_KEY, token);
  else localStorage.removeItem(TOKEN_KEY);
}

// Free Render instances sleep when idle; the first request can take ~1 minute
// and may fail outright while the server boots. Poll /api/health until it answers.
let backendReady: Promise<void> | null = null;

export function waitForBackend(timeoutMs = 120_000): Promise<void> {
  if (!backendReady) {
    const attempt = (async () => {
      const deadline = Date.now() + timeoutMs;
      for (;;) {
        try {
          const res = await fetch(`${BASE}/api/health`);
          if (res.ok) return;
        } catch {
          /* still waking up */
        }
        if (Date.now() > deadline) throw new TypeError("Backend unreachable");
        await new Promise((r) => setTimeout(r, 3000));
      }
    })();
    attempt.catch(() => {
      if (backendReady === attempt) backendReady = null;
    });
    backendReady = attempt;
  }
  return backendReady;
}

async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  const headers = new Headers(init.headers);
  if (init.body) headers.set("Content-Type", "application/json");
  const token = getToken();
  if (token) headers.set("Authorization", `Bearer ${token}`);

  let res: Response;
  try {
    res = await fetch(`${BASE}${path}`, { ...init, headers });
  } catch (err) {
    if (!(err instanceof TypeError)) throw err;
    // Network-level failure (usually a sleeping server): wait for it, retry once.
    backendReady = null;
    await waitForBackend();
    res = await fetch(`${BASE}${path}`, { ...init, headers });
  }
  if (res.status === 401) throw new UnauthorizedError(await errorDetail(res));
  if (!res.ok) throw new Error(await errorDetail(res));
  return res.json();
}

async function errorDetail(res: Response): Promise<string> {
  try {
    const data = await res.json();
    if (typeof data.detail === "string") return data.detail;
    if (Array.isArray(data.detail) && data.detail[0]?.msg) {
      const field = data.detail[0].loc?.at(-1);
      return field ? `${field}: ${data.detail[0].msg}` : data.detail[0].msg;
    }
  } catch {
    /* non-JSON error body */
  }
  return `Request failed (${res.status})`;
}

// ── Auth ──

interface AuthResponse {
  token: string;
  user: User;
}

export async function signup(email: string, password: string, name: string): Promise<User> {
  const data = await request<AuthResponse>("/api/auth/signup", {
    method: "POST",
    body: JSON.stringify({ email, password, name }),
  });
  setToken(data.token);
  return data.user;
}

export async function login(email: string, password: string): Promise<User> {
  const data = await request<AuthResponse>("/api/auth/login", {
    method: "POST",
    body: JSON.stringify({ email, password }),
  });
  setToken(data.token);
  return data.user;
}

export function fetchMe(): Promise<User> {
  return request<User>("/api/auth/me");
}

// ── Catalog ──

export async function fetchCourses(): Promise<Course[]> {
  const data = await request<{ courses: Course[] }>("/api/courses");
  return data.courses;
}

// ── Chat ──

export async function fetchChatHistory(): Promise<ChatMessage[]> {
  const data = await request<{
    messages: { id: number; role: "user" | "assistant"; content: string; tools_used: string[] }[];
  }>("/api/chats");
  return data.messages.map((m) => ({ ...m, id: `db-${m.id}` }));
}

export async function clearChatHistory(): Promise<void> {
  await request("/api/chats", { method: "DELETE" });
}

export function sendChat(message: string): Promise<{ reply: string; tools_used: string[] }> {
  return request("/api/chat", {
    method: "POST",
    body: JSON.stringify({ message }),
  });
}

export function makeId() {
  return Math.random().toString(36).slice(2);
}
