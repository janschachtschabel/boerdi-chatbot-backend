"""Vercel entry point — backend-only deployment.

The Vercel project root is `backend/`, so this file lives at `backend/api/index.py`.
Locally / in Docker this file is unused — `python run.py` keeps working unchanged.
"""

import os
import sys
from pathlib import Path

# Make `backend/` (the parent of `api/`) importable so `from app.main import app`
# works regardless of which directory the function is invoked from.
_BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(_BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(_BACKEND_DIR))

# Vercel-only defaults — only applied when not already set in the dashboard.
os.environ.setdefault("DATABASE_PATH", "/tmp/badboerdi.db")
os.environ.setdefault(
    "BADBOERDI_WIDGET_DIR",
    str(_BACKEND_DIR / "widget_dist"),
)

from app.main import app  # noqa: E402
from app.services.database import init_db  # noqa: E402

# Vercel does NOT run FastAPI's lifespan/startup hooks, so init_db() from
# app.main's lifespan never fires. Run it explicitly here at module import
# time. This happens once per cold start; the SQL is idempotent
# (CREATE TABLE IF NOT EXISTS).
import asyncio  # noqa: E402

try:
    asyncio.run(init_db())
except RuntimeError:
    # Already inside an event loop (shouldn't happen at import time, but
    # just in case): schedule on the running loop instead.
    loop = asyncio.get_event_loop()
    loop.run_until_complete(init_db())

__all__ = ["app"]
