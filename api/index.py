"""Vercel Python entrypoint (file-based function at /api; vercel.json rewrites /api/* here).

Vercel loads the top-level ASGI variable `app`. Locally: `python -m uvicorn api.index:app --reload`.
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.application import app  # noqa: E402,F401
