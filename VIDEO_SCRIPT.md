# Recording guide — 10 minutes maximum

**Critical submission requirement:** record your own screen and voice and publish as an **unlisted YouTube video**, then verify its URL opens in an incognito browser. This script is a guide, not an uploaded video. Speak naturally and show the actual, working app (preferably imported Elexon records). Never represent simulated demo numbers as real results.

## Part 1 — client pitch (0:00–4:45)

**0:00–0:35 — the business problem.** "Tomorrow's electricity procurement depends on how much wind generation is expected. But wind forecasts change during the day. We need to know which forecast was available when traders actually committed their bids—not a more accurate forecast published after the auction."

**0:35–1:15 — the high-level product.** Show the Overview tab. "WindScope transforms Elexon wind generation forecasts and actuals into a point-in-time decision view. The dataset covers decisions from January 1 through January 31, with deliveries on the following day." Show the date selector and the 09:50 UK cutoff.

**1:15–2:15 — today's decision view.** Pick a January decision date, show 24 next-day hourly forecast targets evaluated against averaged half-hour actuals. Point to forecast versus actual chart, the selected day's accuracy, and the forecast publication timestamp in the Hourly Comparisons tab. Explain why a forecast from after 09:50 is excluded.

**2:15–3:20 — forecasting risk.** Show January MAE, RMSE, bias, coverage and daily accuracy. Translate the sign of bias into a trading explanation: positive error indicates less wind arrived than projected, and therefore an increase in potential residual procurement needs. Do *not* claim that this is the utility's net electricity shortfall.

**3:20–4:05 — trust and auditability.** Show CSV export, source links and data coverage. Explain Elexon inputs and why missing data is not filled with zeros.

**4:05–4:45 — conclusion / future scope.** "The pilot already exposes what was known at bidding time and how wind forecasts performed historically. The next step would add customer-owned demand and contract data for portfolio-specific purchasing decisions." If using simulated data, say so up front, explain what is missing, and avoid performance claims.

## Part 2 — technical review (4:45–9:40)

**4:45–5:25 — architecture.** Show repo root. "The React frontend makes requests to a FastAPI backend. The backend reads an Elexon historical snapshot and applies a pure, testable selection and scoring engine. Docker packages the Vite build and Python service."

**5:25–6:20 — ingestion design.** Open `scripts/sync_data.py`. Explain historic publication filtering, daily API requests, retries, the `WIND` fuel filter, snapshot timestamps, and the refusal to silently fabricate missing real data.

**6:20–7:35 — the most important algorithm.** Open `backend/app/analysis.py`. Explain `decision_cutoff()` in Europe/London and `build_rows()`: for each next-day hourly WINDFOR `startTime`, select the last `publishTime <= cutoff`. Describe why the "latest now" forecast would create hindsight leakage, and demonstrate the dedicated unit test.

**7:35–8:20 — metrics.** Show the `metrics()` function. Error = forecast minus actual; MAE, RMSE, bias, coverage, and MW-to-MWh conversion by multiplying by 1 hour after averaging the two FUELHH actual half-hours. Clarify wind overforecast exposure versus real procurement volume.

**8:20–8:55 — API and UI.** Open `backend/app/main.py` and `frontend/src/App.jsx`: typed query inputs, JSON analysis response, CSV export, chart components, date/cutoff controls and the simulated-data warning.

**8:55–9:25 — tests / infrastructure.** Show `pytest`, CI workflow, `Dockerfile`, and `docker-compose.yml`. If deployed, show the Vercel public URL and prove the API returns successfully. Do not claim to have completed checks you have not actually run.

**9:25–9:40 — trade-offs.** "The pilot intentionally excludes demand and prices, because only WINDFOR and FUELHH were allowed. Next priorities would be API schema validation, rolling calibration, and tests over production downloads."

**9:40–10:00 — buffer.** Leave enough time for a clear finish. Keep total under 10:00.

## Recording checklist

- Open the exact deployed app and source repo in **incognito** first.
- Ensure all values represent Elexon actual data before pitching factual findings.
- Use a readable browser zoom and enlarge terminal font if demonstrating code.
- Show URL bar briefly to establish deployed origin.
- Capture your voice clearly. No confidential email or personal information on screen.
- Publish to YouTube as **Unlisted**, verify access in a private browser, then paste its URL in the submission form.
