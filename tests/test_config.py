import os
import subprocess
import sys
from pathlib import Path

import pytest
from starlette.applications import Starlette
from starlette.responses import PlainTextResponse
from starlette.routing import Route
from starlette.testclient import TestClient

from backend.application import EnsureApiPrefix
from backend.config import normalise_database_url

ROOT = Path(__file__).resolve().parent.parent


@pytest.mark.parametrize("raw,expected", [
    ("postgres://u:p@h:5432/db", "postgresql+psycopg2://u:p@h:5432/db"),
    ("postgresql://u:p@h/db?sslmode=require", "postgresql+psycopg2://u:p@h/db?sslmode=require"),
    ("postgres://u:p@h/db?sslmode=require&supa=base-pooler.x", "postgresql+psycopg2://u:p@h/db?sslmode=require"),
    ("postgresql+psycopg2://u:p@h/db", "postgresql+psycopg2://u:p@h/db"),
    ("", ""),
])
def test_database_url_normalisation(raw, expected):
    assert normalise_database_url(raw) == expected


def test_prefix_middleware_adds_api_prefix_only_when_missing():
    async def echo(request):
        return PlainTextResponse(request.url.path)

    inner = Starlette(routes=[Route("/api/x", echo), Route("/api", echo)])
    c = TestClient(EnsureApiPrefix(inner))
    assert c.get("/api/x").text == "/api/x"
    assert c.get("/x").text == "/api/x"  # stripped by a rewrite -> restored


def _run_without_database(code: str, tmp_path) -> subprocess.CompletedProcess:
    env = {k: v for k, v in os.environ.items()
           if k not in ("DATABASE_URL", "POSTGRES_URL", "POSTGRES_URL_NON_POOLING", "TEST_DATABASE_URL")}
    env["PYTHONPATH"] = str(ROOT)
    return subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, env=env, cwd=tmp_path, timeout=120)


def test_app_imports_and_answers_503_without_database(tmp_path):
    code = (
        "from fastapi.testclient import TestClient\n"
        "from api.index import app\n"
        "c = TestClient(app)\n"
        "h = c.get('/api/health'); assert h.status_code == 503 and 'not configured' in h.json()['database'], h.text\n"
        "r = c.get('/api/dashboard/summary'); assert r.status_code == 503 and 'DATABASE_URL' in r.json()['detail'], r.text\n"
        "print('OK')\n"
    )
    out = _run_without_database(code, tmp_path)
    assert out.returncode == 0 and "OK" in out.stdout, out.stderr[-1500:]


def test_postgres_url_alias_is_picked_up(tmp_path):
    code = ("from backend.config import get_settings\n"
            "print(get_settings().database_url)")
    env = {k: v for k, v in os.environ.items() if k not in ("DATABASE_URL", "TEST_DATABASE_URL")}
    env.update(PYTHONPATH=str(ROOT), POSTGRES_URL="postgres://u:p@h/db?sslmode=require&supa=x")
    out = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, env=env, cwd=tmp_path, timeout=60)
    assert out.stdout.strip() == "postgresql+psycopg2://u:p@h/db?sslmode=require", out.stderr[-800:]


def test_cors_is_strict_allow_list_when_enabled(tmp_path):
    code = (
        "from fastapi.testclient import TestClient\n"
        "from api.index import app\n"
        "c = TestClient(app)\n"
        "pre = lambda o: c.options('/api/health', headers={'Origin': o, 'Access-Control-Request-Method': 'GET'})\n"
        "assert pre('https://app.example').headers.get('access-control-allow-origin') == 'https://app.example'\n"
        "assert 'access-control-allow-origin' not in pre('https://evil.example').headers\n"
        "print('OK')\n"
    )
    env = {k: v for k, v in os.environ.items() if k not in ("DATABASE_URL", "TEST_DATABASE_URL")}
    env.update(PYTHONPATH=str(ROOT), CORS_ORIGINS="https://app.example")
    out = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, env=env, cwd=tmp_path, timeout=120)
    assert "OK" in out.stdout, out.stderr[-1000:]
