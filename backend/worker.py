"""Cloudflare Python Workers entry point (wrangler.jsonc → "main").

Render doesn't use this file: it runs `uvicorn app.main:app` from this folder.
Keeping the Workers-only import here means app/main.py still runs anywhere.
"""

from workers import asgi

from app.main import app

Default = asgi.entrypoint(app)
