# TWIN — Smart Factory Security (Vercel-ready, v2)

Cybersecurity dashboard for **simulated** smart-factory digital twins. One Vercel project: React + Vite + TypeScript frontend and a Python FastAPI function at `/api/*`.

**After deploying you see a working dashboard immediately, with no database.** Add PostgreSQL later and the same app switches to persistent storage. The header always shows which mode is active.

| | DEMO MODE | DATABASE CONNECTED |
|---|---|---|
| When | `DATABASE_URL` not set (or DB unreachable, or `DEMO_MODE=true`) | `DATABASE_URL` set and reachable |
| Data | Synthetic factory generated on the server by the real pipeline | PostgreSQL, persistent |
| Persistence | **None.** Regenerated on cold starts, every 10 min and on redeploys; can differ between serverless instances | Yes |
| Actions | Read-only (inject / advance / live mode / resolve are disabled, API answers 409) | Need `ADMIN_API_KEY` |

## Environment variables
| Name | Required | Purpose |
|---|---|---|
| `DATABASE_URL` | no | Hosted PostgreSQL URL (`postgres://` accepted; use the provider's **pooled** URL). `POSTGRES_URL` is also read, so Vercel's Neon/Supabase integrations work as-is. |
| `ADMIN_API_KEY` | only for write actions | Long random string, checked on the backend only (never sent to or bundled in the frontend; you type it into the UI, kept in `sessionStorage`). |
| `DEMO_MODE` | no | `true` forces demo data even if a database is configured. |
| `SIM_DEVICE_COUNT`, `SIM_SEED`, `ACTIVE_WINDOW_MINUTES`, `RETENTION_HOURS`, `ENVIRONMENT`, `CORS_ORIGINS` | no | Tuning (see `.env.example`). |

## Deploy (vercel.com/drop)
1. Upload the project ZIP and deploy. Open the site: **DEMO MODE** dashboard, nothing to configure.
2. *(Optional, for persistence)* Add a PostgreSQL database (e.g. Neon via Vercel → Storage), make sure `DATABASE_URL` is set, set `ADMIN_API_KEY`, then **Redeploy**.
3. Reload. The badge turns to **DATABASE CONNECTED**. The first request after connecting creates the tables and seeds the factory (24 devices, 24 h of telemetry, trained model; a few seconds), exactly once: guarded by a PostgreSQL advisory lock and re-checked inside it, so restarts and concurrent instances never duplicate data.
4. Check `/api/health` and `/api/status` (neither exposes secrets). API docs: `/api/docs`.

If `DATABASE_URL` is set but unreachable, the app does **not** error: it serves demo data, shows "DEMO MODE" with the reason, and retries the database after 30 s.

## Pages
Dashboard, Digital Twin, Threat Detection (click a row for its explanation), Incidents (resolve needs PostgreSQL + admin key), XAI Analysis, Settings (read-only status). *Incident Response, Analytics and Audit Logs are still placeholders.*

## Detection (unchanged)
Simulator → preprocessing → NumPy **Isolation Forest** (`backend/security/iforest.py`) → rule-based **IDS** → threat classification → **risk score** → incidents. Explanations use **occlusion attribution** (reset one feature to its normal value, measure the anomaly-score drop); it is **not SHAP**, and the UI says so. SHAP/scikit-learn were removed because they pushed the Vercel function past its 500 MB bundle limit (installed deps are now ~200 MB).

Measured on simulated data (`python -m scripts.evaluate`, share of attack samples flagged): hybrid 89% / 99% / 100% / 72% (temperature / logins / network / telemetry manipulation), false-positive rate 0.08%; the Isolation Forest alone catches only 6–15%, the IDS rules carry most detections. These figures describe my simulator, not real plant traffic.

## Local development

### Windows PowerShell
```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements-dev.txt
npm ci
# Terminal 1: API (DEMO MODE works without DATABASE_URL)
npm run dev:api
# Terminal 2: frontend
npm run dev
```
Open `http://localhost:5173`. The Vite development server proxies `/api` to `http://127.0.0.1:8000` by default. Set `DEV_API_PROXY` in `.env` if the API uses a different local address.

### macOS / Linux
```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt
npm ci
```
Then run `npm run dev:api` in one terminal and `npm run dev` in another.

Tests: `python -m pytest -q` (DEMO MODE tests need no PostgreSQL). For database-backed API tests, set `TEST_DATABASE_URL=postgresql+psycopg2://USER:PW@localhost:5432/twin_test`; the database name must end in `_test` because tests clear its tables. Frontend checks: `npm run typecheck` and `npm run build`.

## Verification status for this ZIP
- Python suite run during this merge: **31 passed, 1 skipped** without a PostgreSQL test database.
- API import, DEMO MODE startup, telemetry generation, detection, read-only protections and status responses are covered by the passing tests.
- The frontend dependency install/build was **not re-run in this merge environment** because the npm registry fetch could not complete. The ZIP includes the existing `package.json` and `package-lock.json`; Vercel must install dependencies and build the frontend during deployment.
- The merged ZIP has not itself been deployed to Vercel in this verification run. A hosted PostgreSQL connection has not been tested here.

## Manual steps and limits
- DEMO MODE needs no secrets or database setup. It is read-only and its synthetic data is not durable across serverless instances/cold starts or redeploys.
- For persistent mode, configure a hosted PostgreSQL `DATABASE_URL` (prefer the provider's pooled URL), set `ADMIN_API_KEY` for write actions, and redeploy.
- No login/roles are implemented yet; read endpoints are public and the “A. Sharma” profile is a placeholder. Schema creation uses SQLAlchemy `create_all` rather than Alembic migrations. Demo-mode scenario injection is disabled because writes would not persist. Browser-driven live mode advances one tick from an open browser tab; there is no server-side background loop.
