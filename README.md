# TWIN — Enhancing Cybersecurity in Digital Twin Systems for Smart Factories

BE Computer Engineering major project. **Milestone 1** of an incremental build.
Everything is **simulated**: devices, telemetry, attacks and security responses. No real factory or network is touched.

| Layer | Tech |
|---|---|
| Frontend | React 18 + Vite, Recharts, React Router (`frontend/`) |
| Backend | Python 3.12, FastAPI, SQLAlchemy 2 (`backend/`) |
| Database | PostgreSQL |
| AI/ML | pandas, NumPy, scikit-learn Isolation Forest, SHAP |

## What Milestone 1 contains

- **Dashboard** (dark navy UI from the reference): sidebar, 4 summary cards, Digital Twins table, Recent Security Events, Threats Over Time, Anomaly Score Distribution, Device Status donut. Polls the API every 5 s. The header search filters both tables client-side.
- **Factory simulator**: CNC machines, robotic arms, industrial controllers (PLC), temperature and pressure sensors; one digital twin record per device. Scenarios: `abnormal_temperature`, `suspicious_logins`, `network_spike`, `telemetry_manipulation`, plus `device_dropout`.
- **Security pipeline** (`backend/app/security/`): preprocessing → Isolation Forest → rule-based IDS → threat classification → risk assessment. SHAP top-feature explanations are stored on every event (`details.explanation`).
- **API** (`/docs` for OpenAPI): `/api/dashboard/*`, `/api/simulator/*`, `/api/incidents`, `/api/health`.
- Every dashboard number is a query against PostgreSQL. There are no hard-coded statistics.

### How it works
1. `POST /api/simulator/seed` creates the fleet, generates 24 h of 5-minute telemetry, schedules scenarios (4 end within the last ~30 min so the dashboard has live threats), trains the Isolation Forest on the **clean first third only**, then runs the pipeline over all history.
2. Live: `POST /api/simulator/tick` (or the background loop) generates new samples, applies any injected scenarios, and runs the same pipeline with rolling-window history from the DB.
3. Event → severity is `Low/Medium/High/Critical` from `risk = 0.30·ML + 0.30·threat weight + 0.20·device criticality + 0.20·rule evidence`. Critical events open/extend an **incident**; incidents auto-resolve after 60 min without a new Critical event.
4. Dashboard definitions: *Active Threats* = distinct (device, threat class) with a High/Critical event in the last 60 min. *Critical Incidents* = open Critical incidents. *Security score* = `100 − max(0.6·recent max risk, 0.1·latest anomaly score)`.

### Measured detection quality (simulated data only)
`python -m scripts.evaluate` (3 seeds × 24 devices, share of in-scenario samples flagged):

| Scenario | Hybrid (IDS + IF) | IDS rules only | Isolation Forest only | Correct threat class |
|---|---|---|---|---|
| abnormal_temperature | 89% | 89% | 6% | 100% |
| suspicious_logins | 99% | 99% | 21% | 100% |
| network_spike | 100% | 100% | 17% | 100% |
| telemetry_manipulation | 72% | 71% | 11% | 99% |

False-positive rate on clean data: 0.11%.
**Honest reading:** with the current 12 features, a single global model and a threshold at the training 99.9th percentile, the Isolation Forest alone has low recall on these attacks; the rule-based IDS carries most detections. Telemetry manipulation needs an 8-sample window to fill before the flat-line rule fires. Improving the ML side (per-device-type models, feature selection, threshold tuning) is a Milestone 2 candidate. These numbers describe the simulator I wrote, not real industrial traffic.

## Run locally

Prerequisites: Python 3.12, Node 20+, PostgreSQL 14+ (or Docker for `docker-compose.yml`).

```bash
# 1. Database (either use docker...)
POSTGRES_PASSWORD=choose-a-password docker compose up -d
# ...or create it in an existing PostgreSQL:
#   CREATE USER twin WITH PASSWORD '...'; CREATE DATABASE twin OWNER twin; CREATE DATABASE twin_test OWNER twin;

# 2. Backend
cd backend
python -m venv .venv && source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env     # edit DATABASE_URL (password) - never commit .env
uvicorn app.main:app --reload --port 8000

# 3. Frontend (new terminal)
cd frontend
npm install
npm run dev              # http://localhost:5173  (proxies /api to :8000)
```
Open http://localhost:5173 → click **Initialise simulation** (≈3 s). Then use **Simulator** (top right) to inject a scenario and **Advance 10 ticks** / **Start live loop** and watch the cards, tables and charts change.

## Tests
```bash
cd backend
python -m pytest -q                                   # simulator + pipeline tests (no DB needed); API tests skip
TEST_DATABASE_URL=postgresql+psycopg2://twin:PASSWORD@localhost:5432/twin_test python -m pytest -q   # + API tests
python -m scripts.evaluate                            # detection metrics table above
```
`TEST_DATABASE_URL` must point to a database whose name ends in `_test` (the tests TRUNCATE tables; the suite refuses otherwise).
Status on my last run: 23 backend tests passing. There are **no frontend unit tests** yet.

## Deploy

### Backend + PostgreSQL (any container/Python host: Render, Railway, Fly.io, ...)
Vercel is used only for the frontend: the API keeps a PostgreSQL connection pool, holds the optional live-loop task, and writes a model file, none of which suit serverless functions.
1. Create a PostgreSQL instance and a web service from `backend/` (the `Dockerfile` or `Procfile` start command). `render.yaml` is a ready blueprint for Render.
2. Environment variables:

| Variable | Value |
|---|---|
| `DATABASE_URL` | provider connection string (`postgres://` is auto-converted) |
| `ENVIRONMENT` | `production` |
| `CORS_ORIGINS` | your exact Vercel URL, e.g. `https://twin-xyz.vercel.app` (comma-separate several). Optional `CORS_ORIGIN_REGEX` for preview URLs |
| `ADMIN_API_KEY` | long random string. In `production` simulator/mutating endpoints are **refused** if unset |
| `AUTO_SEED` | `true` to seed on first boot if the DB is empty |

3. Check `https://<backend>/api/health` returns `{"status":"ok"}`.

### Frontend → Vercel
1. Push the repo, **Add New → Project**, and set **Root Directory = `frontend`** (Vite is auto-detected; `vercel.json` sets build, output `dist`, SPA rewrite and security headers).
2. Add environment variable **`VITE_API_URL`** = your backend URL (no trailing slash) for Production (and Preview if wanted), then deploy. It is baked in at build time, so redeploy after changing it. A production build without it shows a clear error banner instead of calling localhost.
3. Put the resulting Vercel URL into the backend's `CORS_ORIGINS`.
4. Open the site → **Simulator** → paste the admin key (kept in `sessionStorage`, not in the bundle).

## Known limitations / not done yet
- **Not yet verified:** the Docker image build, `docker-compose.yml`, `render.yaml`, and an actual Vercel deploy. I could only test the local stack (PostgreSQL 16, uvicorn, Vite dev server, headless Chromium).
- No Alembic migrations (`create_all` on startup). No authentication or roles (the "A. Sharma" profile is a static placeholder). Read endpoints are public; only simulator/resolve endpoints take the admin key.
- The sidebar pages other than Dashboard show a "not implemented yet" placeholder (Digital Twin, Threat Detection, Incidents, XAI Analysis, Incident Response, Analytics, Audit Logs, Settings). Incident resolve exists in the API but not the UI.
- The "+2%" twin trend badge and the 4,129-device scale in the reference are not reproduced: the default fleet is 24 simulated devices (`SIM_DEVICE_COUNT`).
- The live loop runs inside one API process (use a single worker). The model file is on local disk; if lost (e.g. redeploy) it is retrained automatically from clean baseline rows in the DB.
- Tests cover simulator, pipeline, API and CORS/admin checks; no load, security, or frontend tests.
