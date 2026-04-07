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

__all__ = ["app"]
