# Houston METRO live vehicle location investigation

## Follow-up: authorized Vehicles access

On September 13, 2026 UTC, a separate Transit Data subscription returned HTTP 200 with `Latitude`, `Longitude`, `VehicleReportTime`, and `IsMonitored`. The adapter found 9 current fresh vehicles on 002, 16 on 082, and 2 on 433; none on 700/800/900 in that check. A later response had 279 rows and 231 fresh current unique vehicles. Of 248 monitored vehicle IDs shared with the initial response, 221 changed coordinates and 237 advanced their report timestamps. This confirms usable moving bus GPS from the separate product. The older access-denial findings below describe the original GTFS-only key.

## Finding

Houston METRO does advertise live bus locations, and its developer portal documents a separate **Vehicles** operation. The immediate obstacle for MetroAI is more specific than a lack of GPS: the application polls a public planner feed that returns no positions, while the configured subscription key is rejected by the separate Transit Data API that exposes Vehicles. The evidence supports testing the correct subscription next, rather than assuming that METRO refuses to release location data.[1][2][3]

This corrects the earlier investigation, which examined GTFS TripUpdates and the public planner but missed the Vehicles operation in the dynamically loaded API catalog. The earlier zero-position measurements remain valid for those endpoints; they were not a complete inventory of METRO's products.

## Official documentation

METRO's rider guide describes green bus icons showing live vehicle locations and direction arrows in the RideMETRO app. It separately explains that arrival displays distinguish tracking estimates from scheduled times. This is evidence of a supported rider-facing location feature, not proof that every bus is tracked at every moment or that every developer subscription includes access.[1]

The developer portal lists two products: **METRO GTFS Realtime** and **METRO Transit Data**. The former's API reference exposes TripUpdates. The latter is described as an OData service provided by a third-party METRO partner. Its operation list includes Routes, Stops, Arrivals, FullRouteInfo, Incidents, and **Vehicles**.[2][3]

The Vehicles operation is `GET https://api.ridemetro.org/data/Vehicles`. Its documentation says it returns current buses and distinguishes monitored records, with realtime information, from scheduled records. The public page does not provide enough detail to validate coordinate field names, timestamp semantics, rail coverage, or update frequency. Those must be established from an authorized response; an operation called Vehicles is not by itself proof that every returned record contains a fresh GPS fix.[2]

The Transit Data product page has a Subscribe action and lists API METRO Transit Data as its included API. Subscription status for the particular account was not visible in the signed-out research browser.[3]

## Controlled endpoint experiments

Tests ran September 12, 2026, around 21:34:31–21:34:33 UTC (4:34 PM Houston time), using the same existing local subscription key. Credentials and keyed URLs were excluded from saved evidence.

- TripUpdates without a key: **401**, missing subscription key.
- TripUpdates with the key header: **200**, 720,823 bytes, **409 trip updates and zero standard VehiclePosition entities**. The feed timestamp was approximately **11 seconds old**, so this was not merely an ancient cached schedule.
- Vehicles with the key header: **401**, invalid key for an active subscription.
- Vehicles with the documented query-key format and no key header: **401**, the same denial.
- Transit Data Routes with the same header: **401**.
- V2 Alerts with the same header: **200**, 37,874 bytes.
- Public planner's network-wide route query: **200**, **109 routes and zero vehicle positions**, counted before MetroAI filtering.

In the authenticated TripUpdates response, route 082 contributed 27 updates, route 002 contributed 10, and route 433 contributed four. No 700/800/900 route IDs appeared in this sample. Those are trip-update counts at one instant, not total fleet sizes or proof that rail has no realtime system.

A preceding check at 21:25:35 UTC returned 392 trip updates and zero VehiclePosition entities. Its public query also returned zero positions across 109 routes, explicitly including 002, 082, 433, 700, 800 and 900. The later 409-update result establishes that the arrival feed changed between observations while the public position feed remained empty. This is a short observation window, not an uptime study.

The script `scripts/probe_metro_access.py` reproduces the authentication controls, protobuf counts, and network-wide GPS check. Detailed output is in `data/metro-access-probe.json`; the earlier counts are in `data/realtime-latest.json`. These files are local evidence and are excluded from Git. Running the script again replaces its latest output.

## What the failures mean

Azure API Management subscriptions may be scoped to a product or an individual API. A key accepted by one product need not be valid for another. Microsoft documents that invalid or incorrectly scoped subscriptions can be rejected by the gateway before a backend call occurs.[4]

The successful arrival and alert controls rule out a globally invalid key. Testing both supported authentication formats reduces the likelihood of a header-name mistake. The denial on both Transit Data Routes and Vehicles strongly suggests a Transit Data subscription-scope problem or a configuration problem affecting that product. It does **not** demonstrate that the Vehicles backend is empty, retired, or unavailable: the experiment never passed authorization.

The two keys attached to one subscription are rotation alternatives, not different API permission levels. Trying the secondary key from the same product is therefore not a sound way to obtain a different product's access.[4]

GTFS separates trip updates from vehicle positions. A trip update may identify a vehicle and predict stop times without carrying its latitude and longitude. Counting vehicle identifiers in TripUpdates as map-ready GPS would be a data-model error.[5]

## Rider complaints and independent evidence

LINK Houston's *Equity in Transit 2025*, page 15, reports that 87% of surveyed riders used one or more tracking apps. It describes nonfunctioning GPS transponders causing scheduled-time fallback and reports that METRO did not track how many trips were accurately covered by realtime information. It also reports improved prediction accuracy, within three minutes approximately 93–94% of the time, compared with 60–70% two years earlier. Accuracy when information exists must not be confused with the share of vehicles for which information exists. These are 2025 report findings, not newly measured 2026 fleet statistics.[6]

An April 20, 2025 r/houston discussion describes inconsistent arrival estimates and a rider who had only once successfully used RideMETRO's GPS tracking. Replies recommend different apps and disagree about accuracy. It documents a rider's experience and confusion about scheduled versus realtime displays; it cannot diagnose the API gateway or quantify system reliability.[7]

An August 2026 r/houston discussion includes both positive reports about RideMETRO tracking and recommendations for Transit crowdsourcing. This counterevidence matters: complaints do not justify declaring the whole tracking system permanently broken.[8]

Transit itself documents that GO users share their vehicle's location with other riders and fill realtime gaps. Therefore, seeing a moving bus in Transit does not establish that the same coordinate came from a publicly available METRO API. It may be crowdsourced.[9]

Search results about Los Angeles Metro outages, WMATA tracking, or other cities were excluded from the Houston diagnosis. Third-party pages advertising Houston tracking were treated as leads, not proof of live coordinate availability or redistribution rights.

## Explanation and remaining uncertainty

Three distinct issues should not be conflated. First, MetroAI's current GPS source is empty. Second, its key is rejected by the more relevant documented Vehicles API. Third, real-world GPS coverage can be intermittent, as the rider report describes. Only the first two were directly measured in this session.

There is no verified evidence here of a deliberate METRO policy withholding all live locations, a security prohibition, a paid-only GPS tier, or a fleet-wide GPS outage. Hardware failures are a documented explanation for some missing rider information, but cannot explain away every empty field in a different API without further evidence.

The working conclusion is **wrong/incomplete source access for MetroAI, with underlying vehicle coverage still to be measured**. Even after a new subscription works, it is possible that the legacy partner service returns scheduled-only records, lacks rail, or has operational problems. Those outcomes remain unresolved.

## Next experiment and application changes

1. Sign in to the METRO portal and open the **METRO Transit Data** product, then request/activate that subscription. If it already exists, verify its state and obtain the key belonging to that specific product.[3]
2. Keep the working GTFS key. Store the new key separately, for example as `METRO_TRANSIT_DATA_API_KEY`; that variable is a proposed addition, not currently implemented behavior.
3. Test Vehicles again. Require HTTP 200 and inspect a small sample for monitored status, actual coordinates, measurement time, vehicle identity, and route/trip identity. Do not invent a parser from assumed column names.
4. Repeat the authorized request at modest intervals and compare timestamps and movement. Check buses 002/082, METRORapid 433, and rail 700/800/900 separately. Some stationary vehicles are normal, so lack of movement alone is not a failure.
5. Once semantics are validated, implement a backend adapter with shared feed caching, explicit unauthorized/unavailable/no-fresh-position states, and correct route matching. Do not issue one entire-fleet fetch per user-selected route.

No subscription was created and no message was sent to METRO during this research. If product access is approved but fails, the useful support question is: “Our GTFS subscription succeeds for TripUpdates, but the Transit Data Vehicles operation rejects access. Which active product/key provides monitored bus coordinates, what are its timestamp semantics, and does it include rail?”

## Sources

1. Houston METRO, [Welcome Aboard — RideMETRO App tracking instructions](https://www.ridemetro.org/riding-metro/transit-services/welcome-aboard). Accessed September 12, 2026.
2. Houston METRO, [API METRO Transit Data — Vehicles](https://api-portal.ridemetro.org/api-details#api=53f1db24ee3f340e949f15c7&operation=53f1db25ee3f34058c6da3ce). Dynamic reference inspected September 12, 2026.
3. Houston METRO, [METRO Transit Data product](https://api-portal.ridemetro.org/product#product=53f1d9e7ee3f340e949f15c5) and [API catalog](https://api-portal.ridemetro.org/apis). Accessed September 12, 2026.
4. Microsoft, [Subscriptions in Azure API Management](https://learn.microsoft.com/en-us/azure/api-management/api-management-subscriptions). Updated December 11, 2025; accessed September 12, 2026.
5. GTFS, [GTFS Realtime Reference](https://gtfs.org/documentation/realtime/reference/). Accessed September 12, 2026.
6. LINK Houston, [Equity in Transit 2025](https://linkhouston.org/wp-content/uploads/2025/09/Equity-in-Transit-2025.pdf), p. 15. 2025; relevant passage available in indexed PDF text, original PDF downloaded for retention.
7. r/houston, [I need help understanding Metro Buses](https://www.reddit.com/r/houston/comments/1k3c077/i_need_help_understanding_metro_buses_i_feel_like/). April 20, 2025. Anecdotal rider accounts.
8. r/houston, [Houston transit first experience](https://www.reddit.com/r/houston/comments/1vna18m/houston_transit_first_experience/). August 2026. Anecdotal rider accounts.
9. Transit, [What is GO crowdsourcing?](https://help.transitapp.com/article/91-what-is-go-crowdsourcing). Accessed September 12, 2026.
