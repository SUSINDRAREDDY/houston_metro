-- Milestone 4: real schema for the existing GTFS data and persistent app state.
CREATE TABLE agency (agency_id TEXT, agency_name TEXT, agency_timezone TEXT);
CREATE TABLE stops (stop_id TEXT PRIMARY KEY, stop_code TEXT, stop_name TEXT,
    stop_lat DOUBLE PRECISION, stop_lon DOUBLE PRECISION, location_type TEXT, parent_station TEXT);
CREATE TABLE routes (route_id TEXT PRIMARY KEY, route_short_name TEXT, route_long_name TEXT,
    route_type INTEGER, route_color TEXT);
CREATE TABLE trips (route_id TEXT, service_id TEXT, trip_id TEXT PRIMARY KEY,
    trip_headsign TEXT, direction_id TEXT, shape_id TEXT);
CREATE TABLE stop_times (trip_id TEXT, arrival_time TEXT, departure_time TEXT, stop_id TEXT,
    stop_sequence INTEGER, pickup_type INTEGER, drop_off_type INTEGER,
    shape_dist_traveled DOUBLE PRECISION, arrival_secs INTEGER, departure_secs INTEGER,
    PRIMARY KEY(trip_id, stop_sequence));
CREATE TABLE calendar (service_id TEXT, monday TEXT, tuesday TEXT, wednesday TEXT,
    thursday TEXT, friday TEXT, saturday TEXT, sunday TEXT, start_date TEXT, end_date TEXT);
CREATE TABLE calendar_dates (service_id TEXT, date TEXT, exception_type INTEGER);
CREATE TABLE shapes (shape_id TEXT, shape_pt_lat DOUBLE PRECISION, shape_pt_lon DOUBLE PRECISION,
    shape_pt_sequence INTEGER, shape_dist_traveled DOUBLE PRECISION);
CREATE TABLE transfers (from_stop_id TEXT, to_stop_id TEXT, transfer_type INTEGER, min_transfer_time INTEGER);
CREATE TABLE feed_info (feed_publisher_name TEXT, feed_start_date TEXT, feed_end_date TEXT, feed_version TEXT);
CREATE TABLE metadata (key TEXT PRIMARY KEY, value TEXT);
CREATE INDEX times_stop_departure ON stop_times(stop_id, departure_secs);
CREATE INDEX trips_service ON trips(service_id);
CREATE INDEX shapes_sequence ON shapes(shape_id, shape_pt_sequence);
CREATE INDEX dates_date ON calendar_dates(date);
-- The separate GIS reference snapshot is preserved, although the router uses GTFS.
CREATE TABLE gis_stations (id TEXT PRIMARY KEY, name TEXT, longitude DOUBLE PRECISION, latitude DOUBLE PRECISION, properties TEXT);
CREATE TABLE gis_metadata (source TEXT, fetched_at TEXT);
CREATE TABLE application_state (key TEXT PRIMARY KEY, value TEXT NOT NULL);
CREATE TABLE uploads (id TEXT PRIMARY KEY, filename TEXT NOT NULL, content_type TEXT NOT NULL,
    size_bytes BIGINT NOT NULL CHECK(size_bytes > 0 AND size_bytes <= 5242880), sha256 TEXT NOT NULL,
    bucket_name TEXT NOT NULL, object_name TEXT NOT NULL UNIQUE, generation TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP);
CREATE TABLE schema_migrations (version TEXT PRIMARY KEY, sha256 TEXT NOT NULL,
    applied_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP);
