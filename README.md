# MetroAI — Group 2

Local Houston transit assistant: Next.js static frontend served by FastAPI, SQLite GTFS routing, current METRO alerts, and OpenRouter free-model intent interpretation. Cloud deployment is deferred at the user's request.

## Run

```sh
uv venv .venv
uv pip install --python .venv/bin/python -r requirements.txt
# Copy .env.example to .env and configure OPENROUTER_API_KEY if needed.
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

Real GTFS trips only. Departure searches cover four hours, with direct or one-transfer journeys, pickup/drop-off restrictions, daily service calendars and exceptions, and previous/next service dates for after-midnight trips. Transfers use the same stop or explicitly published GTFS connections, a minimum three-minute buffer and maximum 60-minute wait. This feed has no transfers.txt, so cross-street walking transfers are not assumed. Results show up to six different route/boarding/alighting combinations. Times are scheduled, not live arrival predictions. Map lines connect actual stops and are labeled as schematic, not street directions.

Current alerts are cached every five minutes while the app runs and marked stale after 15 minutes. Failed refreshes preserve the last successful snapshot. Avoid-alert searches refuse to run with stale/unavailable alerts. Current alerts cannot predict future disruptions. Natural language extracts constraints only and requires review before routing; unsupported requirements produce clarification.

## Refresh and verify

```sh
./scripts/refresh.sh
.venv/bin/python -m pytest -q
```

For daily refresh, add a cron entry using your absolute project path, for example `0 3 * * * cd '/absolute/project/path' && ./scripts/refresh.sh >> data/refresh.log 2>&1`. No system cron was installed automatically. A validated SQLite snapshot replaces the old schedule atomically. Failed downloads/imports retain the old database. Import rejects unsupported frequency-based or untimed-stop feeds rather than publishing incomplete data.

API docs: http://127.0.0.1:8000/docs. Health: `/api/health`; data freshness: `/api/status`.

The live free-model parser, direct and one-transfer timetable routes, calendar exceptions, mode filtering and coverage rejection are verified during development. Free model availability/quotas can fluctuate; manual stop controls remain available.

The running local server also refreshes schedules every 24 hours. To refresh immediately use the script above. AI transient/schema failures get one bounded retry; quota/authentication failures do not trigger retries or key rotation. Tests include free-only enforcement and recovery from a simulated provider failure.

A Dockerfile is supplied for later portability. Docker is not installed on this Mac, so the container build has not been verified; the supported and verified launch path for this local version is scripts/start.sh.

Selected journey maps poll METRO's trip-planner vehicle-position endpoint every 20 seconds. Orange markers are drawn only for reported coordinates updated within 120 seconds. Empty and failed responses are explicitly labeled; scheduled positions are never substituted. At implementation verification, the official endpoint returned no positions for routes 900 and 082. Source: https://planyourtrip.ridemetro.org/ (its public GraphQL endpoint is configured in backend/vehicles.py).
