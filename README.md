# TWIN — Smart Factory Security (Vercel-ready)

Cybersecurity monitoring dashboard for simulated smart-factory digital twins. **All devices, telemetry, attacks and responses are simulated.**
One Vercel project: **React + Vite + TypeScript** frontend and a **Python FastAPI** function, same origin (`/api/*`), hosted **PostgreSQL**.

```
api/index.py          Vercel Python entrypoint (exports ASGI `app`)
backend/              FastAPI app: routers, simulator, security pipeline (Isolation Forest, IDS, risk, SHAP), services
src/                  React + TypeScript dashboard
vercel.json           build, /api rewrite, SPA fallback, function settings
requirements.txt      pinned runtime deps (bundled into the function)   requirements-dev.txt  + uvicorn, pytest
tests/  scripts/      pytest suite, detection evaluation
```

## Environment variables

| Name | Required | Purpose |
|---|---|---|
| `DATABASE_URL` | **yes** | Hosted PostgreSQL URL (`postgres://` / `postgresql://` accepted; use the provider's **pooled** URL). `POSTGRES_URL` is also read, so Vercel's Neon/Supabase integrations work unchanged. |
| `ADMIN_API_KEY` | **yes in production** | Any long random string. Required by every endpoint that changes data (initialise, inject, tick, resolve). If unset on a production/preview deployment those endpoints answer 403. Generate: `python -c "import secrets;print(secrets.token_urlsafe(32))"` |
| `SIM_DEVICE_COUNT`, `SIM_SEED`, `ACTIVE_WINDOW_MINUTES`, `RETENTION_HOURS`, `ENVIRONMENT`, `CORS_ORIGINS` | no | Tuning only; see `.env.example`. CORS is off by default (same origin). |

Never commit `.env`; the ZIP contains only `.env.example`.

## Deploy with vercel.com/drop

1. **Database:** create a PostgreSQL database (e.g. Neon via Vercel → Storage / Marketplace, or any hosted Postgres) and copy its pooled connection string. Tables are created automatically on first request.
2. Go to **https://vercel.com/drop**, upload `TWIN-VERCEL-READY.zip`, deploy. (The first deploy has no database yet; the page loads and shows a "DATABASE_URL is not configured" banner. That is expected.)
3. In the new project: **Settings → Environment Variables** → add `DATABASE_URL` and `ADMIN_API_KEY` (all environments), then **Deployments → ⋯ → Redeploy**. (If you attached a database through the Vercel integration, `DATABASE_URL`/`POSTGRES_URL` is already set.)
4. Open the site → paste your admin key → **Initialise simulation** (a few seconds). Then use **Simulator** (top right) to inject scenarios and advance/live-run the simulation.
5. Check `https://<your-domain>/api/health` → `{"status":"ok","database":"ok",…}`. API docs: `/api/docs`.

No Framework Preset or Root Directory changes are needed: `vercel.json` sets `framework: vite`.

## Local development

```bash
python -m venv .venv && source .venv/bin/activate     # Windows: .venv\Scripts\activate
pip install -r requirements-dev.txt
cp .env.example .env                                   # set DATABASE_URL (a local or hosted Postgres)
npm install
npm run dev:api        # terminal 1 → FastAPI on :8000
npm run dev            # terminal 2 → http://localhost:5173 (Vite proxies /api to :8000)
```
Tests (need Python deps; API tests need a throw-away database whose name ends in `_test`, because they TRUNCATE tables):
```bash
python -m pytest -q                                                    # API tests are skipped without a DB
TEST_DATABASE_URL=postgresql+psycopg2://USER:PW@localhost:5432/twin_test python -m pytest -q
npm run typecheck && npm run build
python -m scripts.evaluate                                             # detection metrics
```

## How it was made serverless-safe

- No background loop: **Live mode** is driven by the browser (one `POST /api/simulator/tick` every 5 s while the tab is open). The server keeps nothing between requests.
- The trained Isolation Forest is stored in PostgreSQL (`model_artifacts`) and cached per warm instance; a cold start loads it from the DB, and if it is missing it retrains from clean baseline rows.
- Lazy DB engine (nothing connects at import), `NullPool` on Vercel, advisory-locked `create_all` once per instance, clean 503s when the DB is missing/unreachable (no connection details leaked).
- One aggregated `GET /api/dashboard/overview` replaces six polling calls (polling pauses while the tab is hidden).
- SHAP is imported lazily, only when an event needs explaining.

## Detection quality (simulated data only)
`python -m scripts.evaluate`, 3 seeds × 24 devices, share of in-scenario samples flagged:

| Scenario | Hybrid | IDS only | Isolation Forest only | Correct class |
|---|---|---|---|---|
| abnormal_temperature | 89% | 89% | 6% | 100% |
| suspicious_logins | 99% | 99% | 21% | 100% |
| network_spike | 100% | 100% | 17% | 100% |
| telemetry_manipulation | 72% | 71% | 11% | 99% |

False-positive rate on clean data 0.11%. The rule-based IDS carries most detections; the Isolation Forest alone has low recall with the current features/threshold (improvement planned). These numbers describe my simulator, not real industrial traffic.

## What was verified, and what was not

Verified in the build sandbox (Python 3.12, Node 22, PostgreSQL 16): clean-venv install of the exact pins (`pip check` clean); **34 pytest tests pass** (simulator, pipeline, API through the real `api.index:app`, CORS/admin-key, URL normalisation, 503 without DB, cold-start model reload); `tsc --noEmit` and `vite build` pass; browser end-to-end of the production build against an empty database (empty state → key rejected → initialise → inject → advance → browser-driven live mode); no `localhost` literal in the bundle and no cross-origin requests; `vercel.json` rewrites/headers compile without error in `@vercel/routing-utils`.

**Not verified (no access to Vercel from the sandbox):** an actual Vercel build/deploy, the deployed function's cold-start time, bundle size accepted by your plan, and a hosted-Postgres connection.

## Manual steps / known risks

- You must supply `DATABASE_URL` and `ADMIN_API_KEY`, then redeploy (env changes apply to new deployments only).
- **Bundle size:** installed dependencies are about 290 MB (≈400 MB with bytecode). Vercel's current docs give a 500 MB uncompressed limit for Python functions; older docs/plans cite 250 MB. If your build fails with a size error, enable Vercel's Large Functions or drop SHAP/pandas-heavy parts (SHAP itself is only ~4 MB, the cost is numpy/pandas/scipy/scikit-learn).
- **Routing model:** this uses the documented file-based `/api` Python function plus an explicit `framework: vite`. Vercel notes that a detected *Python framework preset* takes precedence over `/api` functions, which is why the preset is pinned. If a deploy serves the API for every URL or 404s on `/api/*`, switch to Vercel *Services* (beta; needs the "Services" preset set in the dashboard) or host the API separately.
- **Function time:** `maxDuration` is 60 s (initialisation takes ~3 s locally). Cold starts import pandas/scikit-learn (a few seconds).
- No authentication or roles yet (read endpoints are public; the "A. Sharma" profile is a placeholder). No Alembic migrations (`create_all`). Dashboard pages other than Dashboard are placeholders. No scheduled/automatic ticking: Vercel Cron on the Hobby plan is limited to daily runs, so live mode stays browser-driven.
- Telemetry older than `RETENTION_HOURS` (72) is purged on each tick to bound database growth.
