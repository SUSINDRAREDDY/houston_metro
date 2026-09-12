# Local MVP verification — September 12, 2026

Scope: local only, per user correction. No cloud deployment performed.

- Next.js production export: compilation, TypeScript checks, static export passed.
- FastAPI: home, health, status, stop search, route search, alerts and journey requests returned HTTP 200.
- Official GTFS: validated and imported 120 routes, 8,797 stops, 21,878 trips and 1,415,650 stop times. ZIP SHA-256 fd7e9c3e3f39df060f7da6b9a4aa973cfc5d0febf9d0ecb4b5946c664c5abb23.
- Official GIS: 44 rail station features imported into data/gis.sqlite3.
- Official website alert endpoint: 43 records fetched and cached; subscription API without a key returned 401 as expected.
- Ten tests passed: calendar exceptions, extended GTFS hours, direct and transfer journeys, rail/direct filtering, date coverage, free-only model enforcement, transient AI retry, alert route normalization, stale labeling, and preservation of prior database on malformed feed.
- Live OpenRouter responses correctly extracted both the proposal example and tomorrow/rail/no-transfer constraints. Requests enforce zero-price providers. Provider failure is surfaced and manual controls remain usable.
- Browser: selected stops manually and obtained journeys; final natural-language flow set 17:00 and fewer transfers, then rendered route 900 from UH South University Oaks NB at 17:01 to Central Station Capitol WB at 17:18, plus one-transfer alternatives. Screenshot inspected: leg details and stop map rendered.
- API key excluded from Git and absent from exported JavaScript/HTML.
- Startup script verified on 127.0.0.1:8000. Alert background refresh and daily schedule refresh implemented; daily timer not wall-clock tested for 24 hours. Cron example supplied, no system crontab modified.

Limits: scheduled arrival times, not vehicle predictions; four-hour journey horizon; same-stop transfers for this feed; six route/boarding/alighting alternatives; landmark aliases map to specific stations; public alert endpoint is not a guaranteed developer API. Container recipe supplied but not built because Docker is absent. These limits are documented in README and rider UI where relevant.
