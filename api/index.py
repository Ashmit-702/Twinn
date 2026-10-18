"""Vercel Python entrypoint (file-based function at /api; vercel.json rewrites /api/* here).

Vercel loads the top-level ASGI variable `app`. Locally: `python -m uvicorn api.index:app --reload`.
"""
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# Serverless filesystems are read-only except /tmp; point library caches there.
os.environ.setdefault("NUMBA_CACHE_DIR", "/tmp/numba")
os.environ.setdefault("MPLCONFIGDIR", "/tmp/matplotlib")
os.environ.setdefault("JOBLIB_TEMP_FOLDER", "/tmp")

from backend.application import app  # noqa: E402,F401
