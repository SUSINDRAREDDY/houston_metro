# Houston METRO realtime location and arrival investigation

## Findings

Houston METRO exposes functioning realtime bus arrival predictions. Its public trip-planner GPS query currently returns no vehicles. These are different data products: an arrival update can contain a predicted stop time without providing latitude/longitude. The evidence does not justify claiming that METRO lacks GPS internally, or that its authenticated developer products cannot provide it.[1][2][3]

Two network-wide queries during this investigation each returned HTTP 200 with 109 routes, 293 route patterns and zero vehicle positions. The query used route IDs returned by the server itself, avoiding a guessed route ID or leading-zero mismatch. Empty arrays came directly from the upstream response, before MetroAI's coordinate bounds, timestamp filter, cache or map rendering. This establishes the immediate cause of the empty map: no coordinates in this public upstream response. It does not establish the upstream operational cause.[1]

## Cross-route arrival tests

At 2026-09-12T16:31:24.822273+00:00, 24 stop checks across 12 routes returned 250 departure entries, of which 44 had realtime=true. Entries are stop-level observations, not 250 unique vehicles; the same trip can appear at more than one stop. The sample used up to two route-pattern midpoint stops and ten departures per pattern. It is a bounded diagnostic sample, not a statistical fleet coverage estimate.

- Route 002: 5 realtime entries / 20 departure entries at 2 stops.
- Route 025: 6 realtime entries / 40 departure entries at 2 stops.
- Route 082: 12 realtime entries / 20 departure entries at 2 stops.
- Route 102: 3 realtime entries / 20 departure entries at 2 stops.
- Route 008: 3 realtime entries / 20 departure entries at 2 stops.
- Route 054: 5 realtime entries / 20 departure entries at 2 stops.
- Route 065: 7 realtime entries / 20 departure entries at 2 stops.
- Route 269: 0 realtime entries / 0 departure entries at 2 stops.
- Route 433: 3 realtime entries / 20 departure entries at 2 stops.
- Route 700: 0 realtime entries / 20 departure entries at 2 stops.
- Route 800: 0 realtime entries / 24 departure entries at 2 stops.
- Route 900: 0 realtime entries / 26 departure entries at 2 stops.

All three rail lines (700, 800, 900) returned only SCHEDULED entries in these samples. Route 269 returned no departures at the sampled stops; this is not evidence of a realtime failure, because service availability and day/time differ. Local buses and METRORapid 433 returned UPDATED entries. A subsequent route 082 request also returned realtime=true with a predicted departure 163 seconds later than schedule for trip Houston:12064133. The public arrival feed is therefore not wholly offline.[1]

## Why coordinates can be missing while predictions work

OpenTripPlanner configures trip updates and vehicle positions as separate realtime updaters. A functioning stop-time updater does not imply a configured or healthy vehicle-position updater.[3] Plausible explanations include a position feed not connected to this public planner, an upstream position-feed outage, or a different private product serving vehicle coordinates. These are hypotheses; server configuration and METRO's private API contracts were not accessible, so none can be declared the confirmed root cause.

The field name realtimeDeparture is not sufficient evidence of live information: scheduled records also populate it. The realtime boolean and realtimeState distinguish SCHEDULED from UPDATED. MetroAI must preserve those flags and never label a fallback schedule as live.

## Authenticated developer access

The documented Houston endpoint https://api.ridemetro.org/GtfsRealtime/TripUpdates returned HTTP 401 without a subscription key. METRO's portal instructs developers to sign up and subscribe to APIs.[2] This is an access requirement for that endpoint, not proof that a key will unlock GPS: TripUpdates and VehiclePositions are different GTFS-RT entities.[4] No confirmed Houston VehiclePositions subscription endpoint was found in accessible official documentation. The portal's dynamic API catalog failed to load in the browser; its HTML shell is not an exhaustive API inventory.

## Recommended integration

Use the already verified public stop-arrival endpoint to show an upcoming-departures panel for selected boarding stops, with live/scheduled labels, predicted clock time, delay and request timestamp. Keep these as current departures, distinct from a journey planned for later today or another date. Do not revise a selected future trip using an unrelated current vehicle's prediction. Match trip ID, service date, route and stop before applying any updates to an itinerary.

Retain GPS polling with its explicit empty-data state, but do not promise that it will start working at a particular time. A usable location feed must return vehicle IDs, coordinates, route or trip identifiers and current timestamps; it must also permit the intended use. Ask METRO specifically whether it offers GTFS-RT VehiclePositions or an AVL location API, how bus versus rail coverage differs, and which subscription enables it. A generic request for a realtime API may yield only arrival predictions.

No synthetic moving markers should be presented as actual vehicle positions. Estimating a location from timetable or stop predictions is a separate feature and must be explicitly labeled as estimated.

## Reproduction and evidence

Run `.venv/bin/python scripts/research_realtime.py` from the repository. It makes one network-wide position query and a bounded series of stop-arrival checks, then writes data/realtime-investigation.json. The earlier independent position snapshot is data/live-research-routes.json. Results are timestamped observations, not an uptime guarantee. No developer credentials were exposed, no account was created and no message was sent to METRO.

## Sources

1. METRO official trip planner, https://planyourtrip.ridemetro.org/ ; its deployed JavaScript identifies https://houston-otp-server.ibi-transit.com/otp/gtfs/v1 and the route.patterns.vehiclePositions query. Direct GraphQL responses inspected September 12, 2026; raw results saved locally.
2. Houston METRO developer portal, https://api-portal.ridemetro.org/ ; describes realtime predictions, developer registration and subscriptions. Accessed September 12, 2026.
3. OpenTripPlanner, Realtime Updaters, https://docs.opentripplanner.org/en/v2.4.0/UpdaterConfig/ ; separate TripUpdates and Vehicle Positions updater definitions. Used for architectural interpretation, not proof of METRO's private configuration.
4. GTFS Realtime reference, https://gtfs.org/documentation/realtime/reference/ ; separate TripUpdate and VehiclePosition entities.
5. METRO, Learn How to Ride, https://www.ridemetro.org/riding-metro/transit-services/welcome-aboard ; distinguishes estimated realtime arrivals from scheduled arrivals.
