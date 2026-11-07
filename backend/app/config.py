import os
import re

from dotenv import load_dotenv

load_dotenv()


def _env(name: str, default: str = "") -> str:
    # Tolerate values wrapped in quotes, e.g. PICKUP_STORE='No 19, ...'
    return os.getenv(name, default).strip().strip("'\"").strip()


def _emails(raw: str) -> list[str]:
    # Accepts "a@x.com, b@y.com" or "['a@x.com', ]" — just pull out anything shaped like an email.
    return re.findall(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+", raw)


def _supabase_url(raw: str) -> str:
    # Accept "xyz.supabase.co" or a pasted ".../rest/v1" and normalise to "https://xyz.supabase.co".
    url = raw.rstrip("/").removesuffix("/rest/v1")
    if url and not url.startswith(("http://", "https://")):
        url = "https://" + url
    return url


def _link(raw: str) -> str:
    # A pasted "selar.com/..." would otherwise be treated as a path on our own site.
    return raw if not raw or raw.startswith(("http://", "https://")) else "https://" + raw


SUPABASE_URL = _supabase_url(_env("SUPABASE_URL"))
SUPABASE_SERVICE_KEY = _env("SUPABASE_SERVICE_KEY")

SITE_URL = _env("SITE_URL", "http://localhost:8000").rstrip("/")
KEEPALIVE_INTERVAL_SECONDS = int(_env("KEEPALIVE_INTERVAL_SECONDS", "3600"))

ADMIN_EMAILS = _emails(_env("ADMIN_EMAILS"))
ADMIN_PASSWORD = _env("ADMIN_PASSWORD")
SECRET_KEY = _env("SECRET_KEY")

BREVO_API_KEY = _env("BREVO_API_KEY")
MAIL_FROM_EMAIL = _env("MAIL_FROM_EMAIL")
MAIL_FROM_NAME = _env("MAIL_FROM_NAME", "Beautiful Nothing")
# Where replies go (e.g. the author's personal inbox) when the sender address has no mailbox.
MAIL_REPLY_TO = _env("MAIL_REPLY_TO")

PICKUP_STORE = _env("PICKUP_STORE")
PAPERBACK_DELIVERY_PRICE = int(_env("PAPERBACK_DELIVERY_PRICE", "12000"))
PAPERBACK_PICKUP_PRICE = int(_env("PAPERBACK_PICKUP_PRICE", "10000"))
LAUNCH_GIFT_MINIMUM = int(_env("LAUNCH_GIFT_MINIMUM", "5000"))
EBOOK_PRICE = int(_env("EBOOK_PRICE", "5000"))
PICKUP_AREA = _env("PICKUP_AREA", "Opebi, Ikeja")
# Google Drive link to the ebook file, sent in the thank-you email once a "show love" gift is confirmed.
EBOOK_GIFT_DRIVE_LINK = _link(_env("EBOOK_GIFT_DRIVE_LINK"))

# 'launch'  → landing page leads with "Show love" (gift on Selar ShowLove, ebook as thank-you).
# 'regular' → after launch: landing page sells the ebook through the Selar product page.
SALES_PHASE = _env("SALES_PHASE", "launch")
# Selar links. Empty = button shows "coming soon" (clicks are still counted).
SHOWLOVE_URL = _link(_env("SHOWLOVE_URL"))
EBOOK_URL = _link(_env("EBOOK_URL"))

# Admin session cookie is HTTPS-only once the site runs on https.
SECURE_COOKIES = SITE_URL.startswith("https://")

if not SECRET_KEY:
    # Fine for local dev, but sessions and email links break on every restart. Set it in production.
    import secrets

    SECRET_KEY = secrets.token_urlsafe(48)
