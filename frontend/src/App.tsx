import { useCallback, useEffect, useMemo, useState } from "react";
import { UnauthorizedError, fetchCourses, fetchMe, getToken, setToken } from "./api";
import AuthScreen from "./components/AuthScreen";
import ChatPanel from "./components/ChatPanel";
import CourseCard from "./components/CourseCard";
import CourseModal from "./components/CourseModal";
import type { Course, User } from "./types";
import "./App.css";

const ALL = "All";

const CATEGORY_GROUPS = [
  ALL,
  "Core",
  "Artificial Intelligence",
  "Finance",
  "Marketing",
  "Strategy",
  "Operations",
  "Entrepreneurship & Private Equity",
  "Organizational Behavior",
  "Technology Management",
  "Accounting",
  "Economics",
  "Healthcare Management",
  "Business & the Environment",
  "Real Estate",
  "Nonprofit",
  "PhD",
  "Other",
];

const SESSION_OPTIONS = [ALL, "fall", "fall-1", "fall-2"];

export default function App() {
  const [user, setUser] = useState<User | null>(null);
  const [checking, setChecking] = useState(() => Boolean(getToken()));

  // Restore a saved session on page load.
  useEffect(() => {
    if (!getToken()) return;
    fetchMe()
      .then(setUser)
      .catch((err) => {
        if (err instanceof UnauthorizedError) setToken(null);
      })
      .finally(() => setChecking(false));
  }, []);

  const logout = useCallback(() => {
    setToken(null);
    setUser(null);
  }, []);

  if (checking) {
    return (
      <div className="auth-shell">
        <div className="auth-loading">
          Signing you in… (if the server was asleep, this can take up to a minute)
        </div>
      </div>
    );
  }
  if (!user) return <AuthScreen onAuthed={setUser} />;
  return <Explorer key={user.id} user={user} onLogout={logout} />;
}

function Explorer({ user, onLogout }: { user: User; onLogout: () => void }) {
  const [courses, setCourses] = useState<Course[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [search, setSearch] = useState("");
  const [category, setCategory] = useState(ALL);
  const [session, setSession] = useState(ALL);
  const [selected, setSelected] = useState<Course | null>(null);

  useEffect(() => {
    fetchCourses()
      .then(setCourses)
      .catch(() => setError("Could not load courses. Is the backend running?"))
      .finally(() => setLoading(false));
  }, []);

  const filtered = useMemo(() => {
    const q = search.toLowerCase();
    return courses.filter((c) => {
      const text = [
        c.course_title,
        c.course_number,
        c.faculty_1,
        c.course_description,
      ]
        .join(" ")
        .toLowerCase();

      const matchSearch = !q || text.includes(q);
      const matchCategory =
        category === ALL ||
        c.course_category === category ||
        (category === "Other" &&
          !CATEGORY_GROUPS.slice(1, -1).includes(c.course_category));
      const matchSession = session === ALL || c.course_session === session;

      return matchSearch && matchCategory && matchSession;
    });
  }, [courses, search, category, session]);

  // Derive actual categories from data for display
  const categoryCounts = useMemo(() => {
    const counts: Record<string, number> = {};
    courses.forEach((c) => {
      const cat = c.course_category || "Other";
      counts[cat] = (counts[cat] || 0) + 1;
    });
    return counts;
  }, [courses]);

  return (
    <div className="app-shell">
      {/* ── Header ── */}
      <header className="app-header">
        <div className="header-left">
          <div className="yale-shield">🏛️</div>
          <div>
            <h1 className="app-title">Yale SOM</h1>
            <p className="app-subtitle">Fall 2026 Course Explorer</p>
          </div>
        </div>
        <div className="header-search-wrap">
          <input
            className="search-input"
            type="text"
            placeholder="Search courses, faculty, topics…"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
          {search && (
            <button className="search-clear" onClick={() => setSearch("")}>
              ✕
            </button>
          )}
        </div>
        <div className="header-stats">
          <span className="stat">
            <strong>{filtered.length}</strong> courses
          </span>
        </div>
        <div className="header-user">
          <span className="user-name" title={user.email}>
            {user.name || user.email}
          </span>
          <button className="logout-btn" onClick={onLogout}>
            Sign out
          </button>
        </div>
      </header>

      {/* ── Body ── */}
      <div className="app-body">
        {/* Left: Filters + Grid */}
        <main className="catalog-side">
          {/* Filter bar */}
          <div className="filter-bar">
            <div className="filter-group">
              <label className="filter-label">Category</label>
              <div className="filter-chips">
                {CATEGORY_GROUPS.map((cat) => (
                  <button
                    key={cat}
                    className={`filter-chip ${category === cat ? "active" : ""}`}
                    onClick={() => setCategory(cat)}
                  >
                    {cat}
                    {cat !== ALL && categoryCounts[cat]
                      ? ` (${categoryCounts[cat]})`
                      : cat === ALL
                      ? ` (${courses.length})`
                      : ""}
                  </button>
                ))}
              </div>
            </div>

            <div className="filter-group">
              <label className="filter-label">Session</label>
              <div className="filter-chips">
                {SESSION_OPTIONS.map((s) => (
                  <button
                    key={s}
                    className={`filter-chip ${session === s ? "active" : ""}`}
                    onClick={() => setSession(s)}
                  >
                    {s === ALL ? "All Sessions" : s.replace("-", " ").replace(/\b\w/g, (l) => l.toUpperCase())}
                  </button>
                ))}
              </div>
            </div>
          </div>

          {/* Grid */}
          {loading && (
            <div className="status-msg">Loading courses…</div>
          )}
          {error && (
            <div className="status-msg error">{error}</div>
          )}
          {!loading && !error && filtered.length === 0 && (
            <div className="status-msg">No courses match your filters.</div>
          )}

          <div className="course-grid">
            {filtered.map((c) => (
              <CourseCard
                key={c.id}
                course={c}
                onClick={() => setSelected(c)}
              />
            ))}
          </div>
        </main>

        {/* Right: Chat */}
        <div className="chat-side">
          <ChatPanel onUnauthorized={onLogout} />
        </div>
      </div>

      {/* Modal */}
      {selected && (
        <CourseModal course={selected} onClose={() => setSelected(null)} />
      )}
    </div>
  );
}
