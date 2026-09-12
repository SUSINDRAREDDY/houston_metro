# Cloud Run deployment

Target project: `project-c33c1444-ec13-409f-ac8`. Service: `houston-metro-git`, region `us-south1`.

The Docker image serves both the exported frontend and API. Vercel is optional and has not been configured. The server respects Cloud Run's PORT variable.

## Setup

1. Wait for the GitHub-triggered build of the cloud-data changes to deploy successfully. The setup script uses the image currently deployed on the service; an older image does not contain the refresh command.
2. In an authenticated Cloud Shell, clone the repository (or run `git pull --ff-only` in an existing checkout).
3. Run `bash deploy/setup-cloud-run.sh` from the repository root.

The script creates a private regional bucket, two service accounts, a refresh job, and a daily scheduler. The job imports actual METRO GTFS and publishes only after validation. The first import may take several minutes. The service changes only after that import succeeds. Existing secret environment settings are preserved.

Cloud Run uses request-based CPU allocation, minimum zero instances, maximum two, 2 GiB memory, and concurrency eight. Storage, builds, the scheduled job and network traffic can incur charges even without website visitors. The refresh job receives 4 GiB because import staging files count toward memory.

## Data lifecycle

`GTFS_DB_GCS_URI` identifies the private snapshot. Startup downloads the selected GCS generation into a temporary local file, checks SQLite and required transit tables, then atomically replaces the serving file. Failed refreshes retain the last validated local database. Startup fails if no usable database can be fetched, instead of presenting a ready but empty service.

Incoming API requests check for a changed object at most every 15 minutes per instance. No background GTFS import runs in Cloud Run services. Alerts refresh during applicable requests at most every five minutes, retaining explicit stale/unavailable status on failure. Local development retains its existing refresh loops.

The daily job at 03:00 Houston time downloads and validates GTFS, then replaces the GCS object using a generation precondition. Overlapping jobs cannot overwrite a newer published snapshot. GCS soft delete, if enabled by bucket policy, provides recovery of replaced objects; no unlimited object-version history is enabled by this script.

## Verification

Check `/api/health` returns `status: ok`; `/api/status` returns `ready: true` and nonzero counts. Search stops for UH and Downtown and submit a journey within the feed coverage dates. Check alerts independently. Initial map GPS may remain empty when METRO publishes no vehicle coordinates; this is unrelated to database loading.

Tests cover cold startup, unchanged generation skipping, corrupt snapshot retention, and first-start storage failure. Cloud IAM, job execution and public journey verification must still be tested after setup; local tests do not establish deployment success.

References: https://cloud.google.com/run/docs/container-contract and https://cloud.google.com/python/docs/reference/storage/latest/google.cloud.storage.blob.Blob
