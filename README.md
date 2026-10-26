# MetroAI — Group 2

Local Houston transit assistant: Next.js static frontend served by FastAPI, GTFS routing, current METRO alerts, and OpenRouter free-model intent interpretation. Milestone 4 uses private Cloud SQL PostgreSQL, Cloud Storage uploads, and Secret Manager. See [deployment](docs/MILESTONE4_DEPLOYMENT.md), [recording script](docs/MILESTONE4_RECORDING.md), [written analysis](docs/MILESTONE4_ANALYSIS.md), and the real [SQL migration](migrations/001_managed_state.sql). Earlier Cloud Run setup is documented in [docs/CLOUD_RUN.md](docs/CLOUD_RUN.md).

## Milestone 5: GKE orchestration

The app now has a GKE deployment in `metroai-gke` (`us-central1`), reusing the
Milestone 4 private PostgreSQL database, uploads bucket and Secret Manager identity.
See [manifests and operations](k8s/README.md), [recording guide](docs/MILESTONE5_RECORDING.md),
and [availability analysis](deliverables/milestone5/Written_Analysis.md).
The HTTPS hostname is `metroai.136.81.119.160.sslip.io`; verify the managed certificate
is Active before recording. HPA keeps 2-4 replicas; readiness checks the database
and liveness only checks application response. The VM remains available for the
earlier milestone, with scheduled refresh handed to GKE CronJobs.

## Run

```sh
uv venv .venv
uv pip install --python .venv/bin/python -r requirements.txt
# For local AI use, explicitly export OPENROUTER_API_KEY in your shell.
.venv/bin/python -m backend.ingest
.venv/bin/python -m backend.gis
cd frontend
npm ci
npm run build
cd ..
./scripts/start.sh
```

Open http://127.0.0.1:8000. The configured local `.env` is private and ignored by Git. No credential is sent to the frontend. Only `openrouter/free` or explicit `:free` models are allowed, with zero-price provider constraints. AI requests go to OpenRouter; schedules remain local. Map tiles require internet.

Try “Find me a route from UH to Downtown after 5 PM with fewer transfers.” Review the interpreted stops/preferences, then select Find journeys. UH resolves to UH South University Oaks; Downtown resolves to Central Station. These are explicit demo landmark aliases, not campus-wide geocoding. Exact stops can always be selected.

## Data and research

- Official developer portal: https://api-portal.ridemetro.org/
- Current GTFS ZIP: https://metro.resourcespace.com/pages/download.php?ref=4835&ext=zip
- Official public alerts: https://www.ridemetro.org/metro-api/alerts — the endpoint used by METRO's own alerts page JavaScript. Works without a key; website endpoint stability is not guaranteed.
- Subscription alerts: https://api.ridemetro.org/v2alerts/alerts — requires a METRO developer subscription. Set METRO_API_KEY to use it. The older GtfsAlerts endpoint is retired.
- GIS: METRO_transit_layers/FeatureServer, linked in backend/gis.py. Imported into a separate reference SQLite database; GTFS remains authoritative for routing.
- Schedule semantics: https://gtfs.org/documentation/schedule/reference/
- Free model router: https://openrouter.ai/docs/guides/routing/routers/free-router

Verified download on 2026-09-12: 8,797 stops, 120 routes, 21,878 trips, 1,415,650 stop times. Published feed coverage ends January 23, 2027, although calendar rows extend to February 13; routing respects the earlier published coverage.

## Routing contract

Searches default to **Leave now**, using server time in America/Chicago. Explicit past departure times are rejected. Results identify the date/time searched; an empty result says no matching journey was found in the four-hour window.

With walking enabled (default), METRO's official trip planner supplies bus/rail/walking legs and street-path geometry. We filter its alternatives to the selected mode, up to three transfers, at most 1.2 km total walking, the four-hour window, and alert preferences. Transfers count vehicle changes, not walking legs. Available live arrival updates are labeled separately from scheduled times. This is stop-to-stop planning, not door-to-door address routing, and the upstream planner is an external availability dependency.

With walking disabled, the local GTFS router supports direct or one-transfer journeys, pickup/drop-off restrictions, service calendars/exceptions and after-midnight service. Connections use the same stop or published GTFS transfers, a three-minute minimum buffer and 60-minute maximum wait. Local map lines are schematic stop connections. The current feed has no transfers.txt.

Natural language extracts intent only. Unambiguous stop matches trigger the journey search automatically; ambiguous places require selection. Alerts are cached for five minutes and marked stale after 15 minutes; avoid-alert searches refuse stale/unavailable alerts. Current alerts cannot predict future disruptions. See [data flow and storage](docs/DATA_FLOW.md).

## Refresh and verify

```sh
./scripts/refresh.sh
.venv/bin/python -m pytest -q
```

For daily refresh, add a cron entry using your absolute project path, for example `0 3 * * * cd '/absolute/project/path' && ./scripts/refresh.sh >> data/refresh.log 2>&1`. No system cron was installed automatically. A validated SQLite snapshot replaces the old schedule atomically. Failed downloads/imports retain the old database. Import rejects unsupported frequency-based or untimed-stop feeds rather than publishing incomplete data.

API docs: http://127.0.0.1:8000/docs. Health: `/api/health`; data freshness: `/api/status`.

The live free-model parser, direct and one-transfer timetable routes, calendar exceptions, mode filtering and coverage rejection are verified during development. Free model availability/quotas can fluctuate; manual stop controls remain available.

The running local server also refreshes schedules every 24 hours. To refresh immediately use the script above. AI transient/schema failures get one bounded retry; quota/authentication failures do not trigger retries or key rotation. Tests include free-only enforcement and recovery from a simulated provider failure.

A multi-stage Dockerfile builds the static frontend and Python runtime. Milestone 3 uses `docker-compose.yml`; Milestone 4 uses `deploy/docker-compose.milestone4.yml`, without a data volume or secret environment values. Production credentials come from Secret Manager through the attached VM identity. Local SQLite mode remains available for development; the application does not load `.env` files.

Selected journey maps poll every 20 seconds. With `METRO_TRANSIT_DATA_API_KEY`, positions come from METRO Transit Data's authenticated `/data/Vehicles` endpoint. Only monitored vehicles with recent reports and valid coordinates are shown. The public planner GPS endpoint is a fallback when that key is absent. Bus GPS was verified with the authenticated source; the tested rail routes returned no fresh vehicles. Missing GPS never means no scheduled service. See [the investigation](docs/METRO_LOCATION_INVESTIGATION.md).
