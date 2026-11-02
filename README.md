# Beautiful Nothing — book site

Landing page (and, next, sales page + author dashboard) for *Beautiful Nothing* by Oladimeji Ramon.

```
frontend/   React (Vite) — the public site
backend/    Python (FastAPI) — event tracking, Supabase keep-alive; orders/dashboard API next
supabase/   SQL to run in the Supabase SQL editor
images/     Original images supplied by the author
```

## Run locally

**Backend**

```bash
cd backend
python -m venv .venv
.venv/Scripts/pip install -r requirements.txt    # Windows (use .venv/bin/pip on macOS/Linux)
cp .env.example .env                              # fill in Supabase URL + service-role key
.venv/Scripts/python -m uvicorn app.main:app --reload --port 8000
```

Without Supabase credentials the API still runs and just logs events to the console.

**Frontend**

```bash
cd frontend
npm install
npm run dev        # http://localhost:5173 — /api is proxied to :8000
```

## Supabase

Run [supabase/schema.sql](supabase/schema.sql) in the SQL editor. The backend uses the **service-role key** (server only);
the browser never talks to Supabase directly, and RLS blocks public access to the tables.

## Tracking

The landing page sends three events to `POST /api/events`: `visit` (once per page load), `selah_click`, `order_click`.
Each browser gets an anonymous random ID in localStorage so the dashboard can show unique visitors.

## Keep-alive

`backend/app/keepalive.py` queries the database every `KEEPALIVE_INTERVAL_SECONDS` (default 1 hour) so the
free-tier Supabase project is never paused for inactivity. `GET /api/health` also touches the DB, so if the
backend host itself sleeps when idle, point a free uptime pinger (e.g. cron-job.org, UptimeRobot) at
`/api/health` and both stay awake.

## Before launch

- `frontend/src/config.js` — set `SELAH_URL` once the Selah listing is live (prices live there too).
- Story headings on the landing page ("A body far from home", etc.) are descriptive placeholders — replace with
  the real story titles from the book.
