## Live Application

**Dashboard:** https://kqzwr.vercel.app

**GitHub:** https://github.com/Devkhunger/kqzwr

**Stack:** React, Vite, FastAPI, Python, Docker

**Data:** Elexon BMRS WINDFOR and FUELHH
# WindScope — day-ahead wind procurement intelligence

An anonymous, client-oriented proof of concept for evaluating historic GB day-ahead wind generation forecasts. **React + Vite frontend, Python + FastAPI backend, Docker, Elexon BMRS WINDFOR and FUELHH datasets.**

>**Data provenance:** This repository includes a January 2026 Elexon data snapshot in `data/january_2026.json`, generated using `scripts/sync_data.py`. The application uses WINDFOR forecasts and FUELHH WIND actuals. If the snapshot is unavailable, the dashboard explicitly labels its illustrative sample data. The historical dataset requires source-level validation before operational use.

## Product purpose

Electricity buyers need a useful picture of expected wind availability **as it was known at bid time**. Comparing actual generation to the *last historical forecast* after delivery would leak future knowledge into the evaluation. WindScope reconstructs the decision point for each January 2026 auction, selects the latest forecast eligible at the configurable cutoff, compares it to hourly averages of observed 30-minute wind generation, and quantifies forecast risk.

- **Decisions:** 1–31 January 2026 (inclusive)
- **Delivery:** 2 January–1 February 2026 (inclusive)
- **Default decision cutoff:** 09:50 UK time, matching the published Nord Pool N2EX day-ahead auction gate closure. This is an explicit assumption and can be changed in the UI.
- **Time zone:** Europe/London (GMT in January). Internal join keys and publication eligibility use timezone-aware UTC datetimes.
- **In scope:** Only WIND actual generation from `FUELHH` and historical forecast publications from `WINDFOR`. No demand, prices, procurement, unit commitment, or portfolio modelling.

## Quick start

### Docker (recommended)

```bash
# From the root of this repository
docker compose up --build
# Open http://localhost:8080
```

The bundled January 2026 snapshot is used when available. To regenerate the historical dataset from Elexon, run:

```bash
python -m pip install -r requirements.txt
python scripts/sync_data.py
# Then rebuild Docker so the downloaded JSON is copied into the image:
docker compose up --build
```

The importer requires internet access to the public Elexon BMRS API. Elexon does not require an API key. On ingestion failure it raises an error and refuses to substitute invented data.

### Local development without Docker

Backend:

```bash
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
uvicorn backend.app.main:app --reload --port 8000
```

Frontend (in a second terminal):

```bash
cd frontend
npm install
npm run dev
# Open http://localhost:5173; Vite proxies /api to localhost:8000
```

### Endpoints

- `GET /api/health` — health and snapshot availability
- `GET /api/analysis?decision_date=2026-01-15&cutoff=09:50` — KPIs, selected-day settlement periods, daily MAE, hourly MAE, worst misses
- `GET /api/export.csv?cutoff=09:50` — full January as-of forecast vs actual audit trail, including missing slots
- `GET /docs` — FastAPI OpenAPI specification on the local Python development server (Docker deployment mounts the frontend at `/` but `/docs` remains available)

## How the data analysis works

**1. Ingest.** `scripts/sync_data.py` pages raw `WINDFOR` publications from 30 December 2025 to 1 February 2026 and `FUELHH` actual publications from 2 January to 15 February 2026. The `publishDateTimeFrom` / `publishDateTimeTo` arguments are source-publication windows. The actual API payloads are archived to `data/january_2026.json` with source URLs and retrieval time. Please verify Elexon rate limits, endpoint limits, and publication windows against the current docs before production runs.

**2. Filter.** Keep only FUELHH records whose `fuelType` is exactly `WIND`. Do not synthesize missing observations. For any revised actual record, keep the latest available publication where `publishTime` exists.

**3. Freeze the forecast at decision time.** For each of the 31 trading dates, use its cutoff in `Europe/London`. The evaluated delivery day is exactly the next calendar day. For each hourly WINDFOR `startTime` within that delivery day, select:

```
arg max forecast.publishTime
subject to forecast.startTime == delivery startTime
       and forecast.publishTime <= decision_cutoff
```

If no publication is eligible, the forecast is **missing**, not 0. Late forecasts are never used. The hourly observed value is the arithmetic mean of FUELHH WIND `generation` at that timestamp and 30 minutes later. Both half-hour records are required. No missing data is interpolated.

**4. Quantify error.** Define signed error `e_i = forecast_i − actual_i` (MW). Only hours with a forecast and both underlying half-hour actual values are scored.

| Metric | Definition | Interpretation |
|---|---|---|
| MAE (MW) | `mean(abs(e))` | Average size of error |
| RMSE (MW) | `sqrt(mean(e²))` | Emphasizes large misses |
| Bias (MW) | `mean(e)` | Positive = wind overforecast |
| Coverage (%) | matched hours / 744 hours | Share with measurable performance |
| P90 abs error (MW) | 90th percentile of `abs(e)` | Retrospective magnitude; **not** a point-in-time risk bound |
| Wind overforecast exposure (MWh) | `sum(max(e,0) × 1.0)` | Potential additional energy associated with overforecast wind; **not** net purchased energy |
## AI Assistance

ChatGPT was used to assist with application architecture,
code generation, debugging, test development, and documentation.
The application was built and tested locally using Docker
and deployed to Vercel.
### Important assumptions / limitations

**Mixed source resolutions:** WINDFOR publishes hourly forecasts, while FUELHH actuals are half-hourly. The backtest therefore evaluates **744 hourly forecast targets** (31 × 24), comparing each forecast with the simple average of its two constituent FUELHH observations. This is a power-level approximation for the hour rather than a claim that WINDFOR published distinct half-hour predictions. Any missing constituent reading leaves the hour missing. The original FUELHH half-hour records remain intact in the downloaded source snapshot.


1. The case study is **retrospective**. A January 2026 overall error distribution is not the same as a calibrated uncertainty interval available to a trader on any given January day; producing live ex-ante confidence bands would require training only on preceding observations.
2. Elexon's WINDFOR series covers operationally metered wind farms visible to the system operator. It is not necessarily *all* wind production in the UK or any one retailer's contracted renewable generation.
3. `FUELHH` is an observed/reported half-hourly generation series and may have subsequent revisions. Elexon historical records are used as retrieved; vintage analysis of actuals is outside scope.
4. The forecast's positive error implies a potential increment in residual demand **if all else is constant**, but the app **does not** compute a trade recommendation. It does not have the client's demand, hedges, contracts or pricing data.
5. January dates avoid daylight saving changes, but the logic uses `Europe/London` rather than hardcoding UTC.
6. By design, blank intervals remain blank. Coverage must accompany the accuracy metrics to avoid a misleading sample.
7. The default 09:50 N2EX reference is an assumption; confirm the exact auction, cutoff and internal workflow with the client.

## Project layout

```
api/index.py                  Vercel Python entry point
backend/app/analysis.py      As-of selection, time-zone logic, error metrics
backend/app/demo.py          Deterministic labeled simulated demo data
backend/app/main.py          FastAPI, data source, routes, CSV export
backend/tests/               Unit tests for forecast selection and quality
backend/requirements.txt     Backend dependencies (mirrored at root)
scripts/sync_data.py         Historic Elexon ingestion with retries and validation
frontend/src/App.jsx         Interactive React dashboards, charts and tables
frontend/src/style.css       Responsive custom styles
frontend/vite.config.js      Vite proxy for local development
Dockerfile                   Multi-stage frontend build + Python runtime
docker-compose.yml           Single-command local runtime
vercel.json                  Frontend build and Python API rewrite configuration
.github/workflows/ci.yml     Python tests + frontend build on push
VIDEO_SCRIPT.md              Ready-to-record client and technical presentation
```

## Testing and quality

```bash
python -m pytest backend/tests -q
cd frontend && npm install && npm run build
```

Tests cover the most important failure case: when a **more accurate forecast is published after the cutoff**, it is correctly ignored. Other cases check missing observations, fuel filtering and time-zone handling. GitHub Actions provides a CI smoke check for Python and React. This is a pilot: additional production validation should include API schema contract tests, end-to-end UI tests, duplicate-record audits, data coverage alerts, and verification against Elexon download samples.

## Deployment (Vercel)

1. Create a public GitHub repository with an anonymous/random identifier and push this code.
2. From an internet-connected machine, run `python scripts/sync_data.py` to generate the **real** January snapshot; inspect its coverage and time range before committing it. Unless the snapshot is present at build time, the deployment will show only the clearly labeled simulated preview.
3. Connect the GitHub repo to Vercel and import the project at the repository root. The provided `vercel.json` configures the Vite frontend and routes `/api/*` to `api/index.py`; root `requirements.txt` lists the Python function dependencies. Check that Vercel uses the expected Python runtime and verify routing in deployment logs.
4. Open your public deployment URL and `/api/health` in an **incognito/private** window, test all four tabs and CSV export, and ensure `snapshot_available` is `true` before submitting the historical results.

**Public app URL:** _Not deployed yet — fill in after publishing to your account._

**Public repo URL:** _Not published yet — fill in after creating an anonymous-named repo._

**Unlisted video URL:** _Not recorded/uploaded yet — follow `VIDEO_SCRIPT.md` and add URL before submitting._

The app has not been verified on Vercel or in a Docker runtime in this generated handoff. Treat the deployment instructions as guidance, not evidence of a successful launch.

## Original sources

- [Elexon `WINDFOR` raw stream](https://bmrs.elexon.co.uk/api-documentation/endpoint/datasets/WINDFOR/stream)
- [Elexon `FUELHH` raw stream](https://bmrs.elexon.co.uk/api-documentation/endpoint/datasets/FUELHH/stream)
- [Elexon Insights developer portal](https://developer.data.elexon.co.uk/)
- [Nord Pool N2EX day-ahead gate closure](https://support.nordpoolgroup.com/support/solutions/articles/8000088463-about-the-n2ex-day-ahead-auction)

## AI assistance disclosure

**AI tools were used.** ChatGPT (OpenAI) assisted with domain research, overall system architecture, Python/React code generation, UI styling, test authoring and this documentation. The applicant remains responsible for understanding, auditing and validating all generated code, verifying source data, running builds, deploying the application, and explaining implementation choices to reviewers. Real trading use requires additional validation and controls.

## Future scope

- Point-in-time *rolling* backtests: fit forecast-error distributions on historical days before each decision date.
- Uncertainty bands conditional on forecast level and time of day.
- Upload client-owned demand and supply forecasts, then compute residual procurement in a clearly separated feature.
- Published-data freshness indicators, alerting and reconciliation dashboards.
