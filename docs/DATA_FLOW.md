# MetroAI data flow and storage

## What happens for a request

1. The browser sends the rider's text to FastAPI. OpenRouter's free model extracts places, date/time, mode and transfer preferences. It does not generate journeys or query METRO itself.
2. FastAPI resolves place names against the local SQLite stops table. When no time was requested, the server uses current Houston time. A past explicit departure is rejected.
3. With walking enabled, FastAPI asks the official METRO journey planner for itineraries between the selected stop coordinates. It validates mode, walking distance, transfer count, time window and alerts before returning up to six options. The response supplies each walking and transit leg and path geometry. This searches a bounded set of upstream alternatives, not every possible journey.
4. With walking disabled, the local router computes direct and one-transfer options from SQLite schedules instead.
5. Alerts are attached from a short-lived cache. Vehicle locations are fetched separately when viewing a route. Missing GPS is shown as missing GPS; it does not suppress scheduled journeys.

The application does **not** save prompts, user query history or computed journey results to the database. Connected-planner responses are returned to the browser without persistence. AI and METRO receive their respective requests; this description concerns our application's storage.

## Schedule database

METRO GTFS ZIP → daily Cloud Run refresh job → validated SQLite snapshot → private Cloud Storage object → local snapshot in each Cloud Run service instance.

SQLite holds routes, stops, trips, stop_times, calendars, exceptions, shapes, transfers and feed metadata. Stop times reference trips; trips reference routes and service calendars. We import the whole timetable once per refresh, not once per rider query. Only the refresh job publishes the shared snapshot. The service downloads it on startup and checks for a newer generation on traffic, at most every 15 minutes. Atomic replacement preserves complete snapshots.

Cloud Storage is durable storage for the database file, not a live SQL server. Each instance queries its own copy. This is appropriate for read-heavy public schedules; application instances must not write user records into that snapshot.

Alerts use a five-minute refresh cache (stale after 15 minutes). Vehicle responses use a 20-second in-memory cache per instance and only reports up to 120 seconds old are displayed. These caches are not permanent tracking histories.

## If we add accounts or history

Keep public timetable snapshots as they are. Add a separate durable application database only when favorites/accounts/history are required: Firestore fits simple per-user favorites; PostgreSQL fits relational history and analytics. Store user-owned data there, with explicit retention choices. Do not save every location response or route result by default; those become stale quickly.

## Current routing boundary

Connected mode supports bus, rail and walking, up to three vehicle changes and 1.2 km total walking within four hours. Walking steps come from METRO's planner. Endpoints remain selected transit stops; address geocoding, guaranteed accessibility, fares and arrive-by searches are not implemented. The local fallback supports at most one transfer and no inferred street walking. An unavailable external planner is reported as an error, distinct from zero matching journeys.
