# Beautiful Nothing — book site

Landing page, paperback ordering and admin dashboard for *Beautiful Nothing* by Oladimeji Ramon.
One Python app: **FastAPI + Jinja2 templates**, data in **Supabase**, emails through **Brevo**.

```text
backend/
  app/
    main.py        app setup, /api/events (tracking), /api/health
    site.py        public pages: landing, show love, order, order status, acknowledge link
    admin.py       /admin pages (password login, signed cookie)
    orders.py      order lifecycle (allowed status changes, history, emails)
    emails.py      email templates + Brevo sending
    db.py          small async client for Supabase's REST API (httpx)
    content.py     landing-page copy (stories, timeline)
    templates/     Jinja2 pages
    static/        css, js (animations, tracking, live order total), images
supabase/schema.sql   run once in the Supabase SQL editor
images/               original images supplied by the author
```

## How buying works

| | Launch (`SALES_PHASE=launch`) | After launch (`SALES_PHASE=regular`) |
| --- | --- | --- |
| Digital | **Show love**: visitor leaves name + email, then goes to Selar ShowLove. Admin matches names on Selar, then clicks **Thank** (sends thank-you + ebook link). | **Buy ebook**: straight to the Selar product page. Selar handles payment and delivery. |
| Paperback | ₦12,000 delivered (Lagos only) or ₦10,000 pickup at the store. Paid by bank transfer. | same |

Change the phase, prices, Selar links, ebook gift link, notification emails and pickup locations in
**/admin → Settings**. They apply immediately (stored in Supabase; the `.env` values are only the starting values).

**After paying on Selar**, set Selar's redirect / "after purchase" link so buyers land on the thank-you page:

- ShowLove page → `<SITE_URL>/thank-you?from=showlove`
- Ebook product → `<SITE_URL>/thank-you?from=ebook`

### Paperback order chain

```text
Buyer places order  ─► order code (BN-0001) + bank accounts       ✉ buyer: payment details   ✉ admin: new order
Buyer taps "I've sent the money" (name + bank they paid from)      ✉ admin: what to look for in the bank alert
Admin checks the bank alert, taps Acknowledge in /admin            ✉ buyer: payment confirmed
Admin: Mark out for delivery / ready for pickup                    ✉ buyer
Admin: Mark delivered / picked up                                  ✉ buyer
(side paths: Payment not found → buyer confirms again; Cancel)
```

No screenshot upload: the buyer says which account the money came from on their order page, and the
admin confirms against the real bank alert. Emails have no buttons; buyers who closed their order page
reopen it at `/order/find` with their order number and email. Admin actions happen in /admin.
People outside Lagos can join a waitlist instead.

## Setup

### 1. Supabase

Run [supabase/schema.sql](supabase/schema.sql) in the **SQL editor**. Everything is prefixed `bn_`, so it
sits safely beside other apps in the same project. It also seeds the two bank accounts; more can be
added from /admin.

### 2. Environment (`backend/.env`, see [.env.example](backend/.env.example))

| Variable | Where it comes from |
| --- | --- |
| `SUPABASE_URL` | Supabase → Project Settings → API → Project URL |
| `SUPABASE_SERVICE_KEY` | Supabase → Project Settings → API keys → `service_role` (legacy tab) or the new secret key. **Server only.** |
| `SITE_URL` | The public address of the site (used in email links) |
| `ADMIN_EMAILS` | Who gets order notifications (comma-separated) |
| `ADMIN_PASSWORD` | Password for `/admin` |
| `SECRET_KEY` | Long random string (already generated in your local `.env`) |
| `BREVO_API_KEY` | brevo.com → SMTP & API → API keys (free: 300 emails/day) |
| `MAIL_FROM_EMAIL` | A sender verified in Brevo → Senders |
| `SALES_PHASE`, `SHOWLOVE_URL`, `EBOOK_URL`, prices, `EBOOK_GIFT_DRIVE_LINK` | Starting values only; change them later in /admin → Settings |

Without Brevo the site still works and prints emails to the console instead of sending them.

### 3. Hosting

**Render** (works today): new **Web Service** from the GitHub repo:

- Root directory: `backend`
- Build command: `pip install -r requirements.txt`
- Start command: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
- Environment: every variable above

Render's free tier sleeps after ~15 min idle. Add a free **UptimeRobot** HTTP(s) monitor on
`https://<your-service>.onrender.com/api/health` every 5 minutes; it keeps the site awake, and
`/api/health` also queries the database so Supabase stays active.

**Cloudflare Python Workers** (planned): the app is async and uses plain `httpx` (no Supabase library),
so it's ready to try there. It still needs a small Worker entry file, and a test that the free plan's
10 ms CPU limit per request holds.

## Run locally

```bash
cd backend
python -m venv .venv && .venv/Scripts/pip install -r requirements.txt
.venv/Scripts/python -m uvicorn app.main:app --reload --port 8000    # http://localhost:8000
```

## Tracking

Events posted to `/api/events`: `visit` (once per landing-page view), `showlove_click`, `ebook_click`,
`order_click`. Each browser gets an anonymous random ID so the dashboard can count unique visitors.
