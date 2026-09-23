# Yale SOM Course Explorer

A React + FastAPI + PydanticAI app for browsing the Yale SOM Fall 2026 catalog and chatting with a course-advisor agent.

- **Catalog grid** loads courses from the `courses` database table.
- **Chat agent** (PydanticAI through Portkey) has a `search_courses` tool that queries the `courses` table, plus a `web_search` tool.
- **Accounts:** a sign-in / create-account screen sits in front of the app. Passwords are stored as bcrypt hashes, and the salt is part of the hash string.
- **Saved chats:** every message is written to the `chats` table, so each user's conversation is reloaded when they sign back in, and the agent can see earlier messages.

```
backend/    FastAPI app (main.py), agent.py, tools.py, db.py, auth.py
frontend/   React + Vite + TypeScript
data/       yale_som.db (local SQLite; not committed)
```

## Database

| table     | contents                                                           |
|-----------|--------------------------------------------------------------------|
| `courses` | SOM catalog (ships in `yale_som.db`)                               |
| `users`   | `id, email (unique), name, password_hash, created_at`              |
| `chats`   | `id, user_id → users.id, role, content, tools_used, created_at`    |

The backend reads `DATABASE_URL`. If it's unset, the app uses `data/yale_som.db` (SQLite). If it's a Postgres URL (Supabase), the app uses that. When the app starts it creates the `users` and `chats` tables if they don't exist yet.

## Run locally

1. Download [data.zip](https://zlisto.github.io/mgt_409_fa26/lectures/data/lec08/data.zip) and unzip it here so you have `data/yale_som.db`.
2. `cp .env.example .env` and set `PORTKEY_API_KEY`.
3. Backend:
   ```bash
   cd backend
   python -m venv .venv
   .venv\Scripts\activate        # macOS/Linux: source .venv/bin/activate
   pip install -r requirements.txt
   uvicorn main:app --port 8000
   ```
4. Frontend (in a second terminal):
   ```bash
   cd frontend
   npm install
   npm run dev
   ```
5. Open http://localhost:5173 and create an account.

## Deploy

### 1. GitHub
Push this folder to a GitHub repo. `.gitignore` keeps out `.env`, `data/` (your local users and password hashes), `node_modules/`, and `.venv/`.

### 2. Supabase (database)
1. Create a project at [supabase.com](https://supabase.com) and save the database password.
2. Click **Connect** and copy the **Session pooler** URI. It looks like
   `postgresql://postgres.<ref>:<password>@aws-0-<region>.pooler.supabase.com:5432/postgres`.
   Render doesn't support IPv6, so use the pooler rather than the "Direct connection" host.
3. Copy the catalog into Supabase from your laptop:
   ```bash
   cd backend
   python migrate_to_supabase.py "postgresql://postgres.<ref>:<password>@...pooler.supabase.com:5432/postgres"
   ```
   This creates `courses`, `users`, and `chats` in Supabase and copies all 234 courses. Add `--with-users` if you also want to copy local accounts and chats.

### 3. Render: backend (Web Service), deploy this first
- **Root Directory:** `backend`
- **Runtime:** Python
- **Build Command:** `pip install -r requirements.txt`
- **Start Command:** `uvicorn main:app --host 0.0.0.0 --port $PORT`
- **Environment variables:**
  - `PORTKEY_API_KEY`: your Portkey key
  - `DATABASE_URL`: the Supabase Session pooler URI
  - `JWT_SECRET`: a long random string (Render's "Generate" button works)
  - `FRONTEND_ORIGIN`: leave unset for now, then set it to the Static Site URL after step 4

Check `https://<backend>.onrender.com/api/health`. It should show `"database": "postgresql", "courses": 234`.

### 4. Render: frontend (Static Site)
- **Root Directory:** `frontend`
- **Build Command:** `npm ci && npm run build`
- **Publish Directory:** `dist`
- **Environment variable:** `VITE_API_URL` = `https://<backend>.onrender.com`

Then go back to the backend service, set `FRONTEND_ORIGIN=https://<frontend>.onrender.com`, and let it redeploy.

Secrets (`PORTKEY_API_KEY`, the Supabase URL, `JWT_SECRET`) belong only in `.env` locally and in Render's Environment tab. Never put them in the repo.
