#!/usr/bin/env bash
# Run from an updated checkout in an authenticated Google Cloud Shell.
set -euo pipefail
PROJECT=project-c33c1444-ec13-409f-ac8
REGION=us-south1
SERVICE=houston-metro-git
BUCKET="${PROJECT}-metro-data"
URI="gs://${BUCKET}/metro.sqlite3"
JOB=metro-refresh
JOB_SA="metro-refresh@${PROJECT}.iam.gserviceaccount.com"
SCHEDULER_SA="metro-scheduler@${PROJECT}.iam.gserviceaccount.com"
IMAGE=$(gcloud run services describe "$SERVICE" --project="$PROJECT" --region="$REGION" --format='value(spec.template.spec.containers[0].image)')
RUNTIME_SA=$(gcloud run services describe "$SERVICE" --project="$PROJECT" --region="$REGION" --format='value(spec.template.spec.serviceAccountName)')
if [[ -z "$IMAGE" || -z "$RUNTIME_SA" ]]; then
  echo 'Cannot determine the deployed image or runtime service account.' >&2
  exit 1
fi
gcloud storage buckets describe "gs://${BUCKET}" --project="$PROJECT" >/dev/null 2>&1 || \
  gcloud storage buckets create "gs://${BUCKET}" --project="$PROJECT" --location="$REGION" --uniform-bucket-level-access --public-access-prevention
for name in metro-refresh metro-scheduler; do
  gcloud iam service-accounts describe "${name}@${PROJECT}.iam.gserviceaccount.com" --project="$PROJECT" >/dev/null 2>&1 || \
    gcloud iam service-accounts create "$name" --project="$PROJECT"
done
gcloud storage buckets add-iam-policy-binding "gs://${BUCKET}" --member="serviceAccount:${RUNTIME_SA}" --role=roles/storage.objectViewer >/dev/null
gcloud storage buckets add-iam-policy-binding "gs://${BUCKET}" --member="serviceAccount:${JOB_SA}" --role=roles/storage.objectUser >/dev/null
# The job imports and validates GTFS before replacing the shared object.
gcloud run jobs deploy "$JOB" --project="$PROJECT" --region="$REGION" \
  --image="$IMAGE" --service-account="$JOB_SA" --command=python --args=-m,backend.cloud_data \
  --set-env-vars="GTFS_DB_GCS_URI=${URI},DATA_DIR=/app/data" \
  --memory=4Gi --cpu=1 --tasks=1 --parallelism=1 --max-retries=1 --task-timeout=3600s
# Do not switch the service until the initial import succeeds.
gcloud run jobs execute "$JOB" --project="$PROJECT" --region="$REGION" --wait
gcloud run services update "$SERVICE" --project="$PROJECT" --region="$REGION" \
  --update-env-vars="GTFS_DB_GCS_URI=${URI},DATA_DIR=/app/data" \
  --memory=2Gi --cpu=1 --scaling=auto --min=0 --min-instances=0 --max=2 --concurrency=8 --cpu-throttling --timeout=300s
gcloud run jobs add-iam-policy-binding "$JOB" --project="$PROJECT" --region="$REGION" \
  --member="serviceAccount:${SCHEDULER_SA}" --role=roles/run.invoker >/dev/null
# Scheduler uses OAuth for the Google Run API, rather than a public application endpoint.
SCHEDULER_ACTION=create
if gcloud scheduler jobs describe metro-daily-refresh --project="$PROJECT" --location="$REGION" >/dev/null 2>&1; then
  SCHEDULER_ACTION=update
fi
gcloud scheduler jobs "$SCHEDULER_ACTION" http metro-daily-refresh --project="$PROJECT" --location="$REGION" \
  --schedule='0 3 * * *' --time-zone=America/Chicago \
  --uri="https://run.googleapis.com/v2/projects/${PROJECT}/locations/${REGION}/jobs/${JOB}:run" \
  --http-method=POST --oauth-service-account-email="$SCHEDULER_SA"
echo 'Setup complete. Check /api/health and /api/status on the deployed service.'
