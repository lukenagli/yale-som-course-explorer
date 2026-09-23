import { useEffect, useRef, useState } from "react";
import {
  UnauthorizedError,
  clearChatHistory,
  fetchChatHistory,
  makeId,
  sendChat,
} from "../api";
import type { ChatMessage } from "../types";
import "./ChatPanel.css";

const SUGGESTIONS = [
  "Who teaches MGT 409?",
  "How many core courses are there?",
  "What are some good AI courses?",
  "What courses meet on Mondays?",
];

const TOOL_LABELS: Record<string, string> = {
  search_courses: "🔍 search_courses",
  web_search: "🌐 web_search",
};

const WELCOME: ChatMessage = {
  id: "welcome",
  role: "assistant",
  content:
    "Hi! I'm your Yale SOM course advisor 🎓\n\nAsk me anything about Fall 2026 courses — faculty, schedules, categories, or course content.",
};

interface Props {
  onUnauthorized: () => void;
}

export default function ChatPanel({ onUnauthorized }: Props) {
  const [messages, setMessages] = useState<ChatMessage[]>([WELCOME]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [historyLoading, setHistoryLoading] = useState(true);
  const bottomRef = useRef<HTMLDivElement>(null);

  // Load this user's saved conversation.
  useEffect(() => {
    let cancelled = false;
    fetchChatHistory()
      .then((saved) => {
        if (!cancelled) setMessages([WELCOME, ...saved]);
      })
      .catch((err) => {
        if (err instanceof UnauthorizedError) onUnauthorized();
      })
      .finally(() => {
        if (!cancelled) setHistoryLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [onUnauthorized]);

  async function clearHistory() {
    if (loading || !window.confirm("Delete your saved chat history?")) return;
    try {
      await clearChatHistory();
      setMessages([WELCOME]);
    } catch (err) {
      if (err instanceof UnauthorizedError) onUnauthorized();
    }
  }

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  async function submit(text?: string) {
    const content = (text ?? input).trim();
    if (!content || loading || historyLoading) return;
    setInput("");

    const userMsg: ChatMessage = { id: makeId(), role: "user", content };
    const loadingId = makeId();
    const loadingMsg: ChatMessage = {
      id: loadingId,
      role: "assistant",
      content: "",
      loading: true,
    };

    setMessages((prev) => [...prev, userMsg, loadingMsg]);
    setLoading(true);

    try {
      const data = await sendChat(content);
      setMessages((prev) =>
        prev.map((m) =>
          m.id === loadingId
            ? { ...m, content: data.reply, tools_used: data.tools_used, loading: false }
            : m
        )
      );
    } catch (err) {
      if (err instanceof UnauthorizedError) {
        onUnauthorized();
        return;
      }
      setMessages((prev) =>
        prev.map((m) =>
          m.id === loadingId
            ? {
                ...m,
                content:
                  err instanceof TypeError
                    ? "⚠️ Couldn't reach the backend. Make sure it's running."
                    : `⚠️ ${(err as Error).message}`,
                loading: false,
              }
            : m
        )
      );
    } finally {
      setLoading(false);
    }
  }

  function handleKey(e: React.KeyboardEvent) {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      submit();
    }
  }

  const showSuggestions = !historyLoading && messages.length === 1;

  return (
    <aside className="chat-panel">
      <div className="chat-header">
        <span className="chat-header-icon">💬</span>
        <div>
          <div className="chat-header-title">Course Advisor</div>
          <div className="chat-header-sub">gpt-5.6-luna · PydanticAI · history saved</div>
        </div>
        {messages.length > 1 && (
          <button className="chat-clear-btn" onClick={clearHistory} disabled={loading}>
            Clear
          </button>
        )}
      </div>

      <div className="chat-messages">
        {historyLoading && <div className="history-loading">Loading your chat history…</div>}
        {messages.map((msg) => (
          <div key={msg.id} className={`chat-bubble-wrap ${msg.role}`}>
            <div className={`chat-bubble ${msg.role}`}>
              {msg.loading ? (
                <div className="typing-indicator">
                  <span /><span /><span />
                </div>
              ) : (
                <p className="bubble-text">{msg.content}</p>
              )}
            </div>

            {msg.tools_used && msg.tools_used.length > 0 && (
              <div className="tool-calls">
                {msg.tools_used.map((tool) => (
                  <span key={tool} className="tool-chip">
                    {TOOL_LABELS[tool] ?? `⚡ ${tool}`}
                  </span>
                ))}
              </div>
            )}
          </div>
        ))}
        <div ref={bottomRef} />
      </div>

      {showSuggestions && (
        <div className="suggestions">
          {SUGGESTIONS.map((s) => (
            <button key={s} className="suggestion-btn" onClick={() => submit(s)}>
              {s}
            </button>
          ))}
        </div>
      )}

      <div className="chat-input-area">
        <textarea
          className="chat-input"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={handleKey}
          placeholder="Ask about courses, faculty, schedules… (Enter to send)"
          rows={2}
          disabled={loading || historyLoading}
        />
        <button
          className="send-btn"
          onClick={() => submit()}
          disabled={loading || !input.trim()}
        >
          {loading ? "…" : "↑"}
        </button>
      </div>
    </aside>
  );
}
