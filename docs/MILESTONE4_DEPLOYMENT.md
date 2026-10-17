# Milestone 4 deployment

Project: `metroai-vm-milestone-20260922`. Region: `us-central1`.

The production container uses Cloud SQL PostgreSQL, a private Cloud Storage
bucket, and Secret Manager. There is no data-volume or `.env` mount. The
filesystem is read-only apart from `/tmp`, a disposable memory filesystem.
API credentials are fetched into process memory with the VM's metadata identity.
The Cloud SQL Python Connector uses that same identity and private TLS access.

## Resources and identity

- VM: `metroai-vm`, `us-central1-a`, public address `35.202.153.219:8000`.
- VM subnet: `metroai-subnet`, `10.42.0.0/24`, VPC `metroai-vpc`.
- Cloud SQL: `metroai-postgres`, PostgreSQL 16, `db-f1-micro`, 10 GB SSD,
  private `10.164.0.3`, public IP disabled; Private Services Access range
  `10.164.0.0/16`. Daily backups keep seven copies. Deletion protection is on.
- Bucket: `gs://metroai-vm-milestone-20260922-uploads`, uniform bucket IAM,
  public access prevented. Stores `uploads/`, `migration-backups/`, and `recovery/`.
- VM service account:
  `metroai-runtime@metroai-vm-milestone-20260922.iam.gserviceaccount.com`.
- Project role: Cloud SQL Client. Bucket role: Storage Object User.
  Registry repository role: Artifact Registry Reader. Secret role: Secret
  Manager Secret Accessor on each of the four runtime secrets only.
- Secrets: `metroai-openrouter-api-key`, `metroai-metro-api-key`,
  `metroai-transit-data-api-key`, `metroai-db-password`, and the separate
  `metroai-db-admin-password`. The runtime identity cannot read the admin secret.
- No user-managed service account keys. `cloud-platform` OAuth scope is
  constrained by the resource IAM grants above.

The database user `metroai_app` has the database privileges needed by this
student app and its schema, but is not the Cloud SQL administrator. Its password
is stored in Secret Manager. API requests bind user values separately from SQL.

## Migration

`migrations/001_managed_state.sql` defines real PostgreSQL tables and indexes.
`python -m scripts.migrate_state` applies that file and copies the consistent
SQLite snapshot in one transaction. It refuses to overwrite an already applied
migration. The row-count report includes all 11 transit tables and the separate
two GIS reference tables. Alert JSON is preserved as managed application state.
The original snapshots are also retained in the private bucket.

The daily refresh stages new GTFS data in disposable `/tmp` storage, validates
it, then replaces only the transit tables in a PostgreSQL transaction. It does
not truncate uploads, alert cache, GIS references, or migration history. The
refresh task stops while the VM is down; the last validated database survives.

## Run the current deployment

Inside the VM:

```bash
sudo systemctl status metroai-milestone4 --no-pager
sudo docker compose -p metroai-m4 -f /opt/metroai/docker-compose.milestone4.yml ps
curl -fsS http://localhost:8000/api/status
```

The startup script uses a temporary Docker configuration and discards the
short-lived registry token after the pull. It does not create a credential file
in the app image or container. Secrets are not injected as Compose environment
values. Nonsecret configuration names remain visible in Compose.

## Recover after VM deletion

Do not delete the current VM for the demonstration. A replacement VM must use
the same VPC/subnet, service account, firewall tag, and reserved IP. The private
bucket has the three nonsecret deployment files; the following startup script
installs Docker and loads them using metadata identity. An operator with normal
Compute permissions can create a replacement after confirming the old VM no
longer owns the reserved IP:

```bash
gcloud compute instances create metroai-vm \
  --project=metroai-vm-milestone-20260922 --zone=us-central1-a \
  --machine-type=e2-small --image-family=ubuntu-2404-lts-amd64 \
  --image-project=ubuntu-os-cloud --boot-disk-size=20GB \
  --subnet=metroai-subnet --address=35.202.153.219 --tags=metroai-demo \
  --service-account=metroai-runtime@metroai-vm-milestone-20260922.iam.gserviceaccount.com \
  --scopes=cloud-platform \
  --metadata-from-file=startup-script=deploy/recover_milestone4_startup.sh
```

The recovery command is prepared, not a claim that the VM was deleted and
recreated during testing. Container recreation is the nondestructive state
persistence check. Recovery is operator-driven, not automatic failover.

## Boundaries and costs

The app has no user-account system; this coursework demo is restricted to the
presenter's IP by the VM firewall. Bucket objects remain private, and downloads
are proxied by the app as attachments. Change the source `/32` if the presenter
changes networks, rather than exposing the demo globally. Uploads are limited
to 5 MB. Invalid filenames, empty uploads, and oversize requests are rejected.

The Cloud SQL tier is zonal and not highly available. A VM deletion stops the
website, in-flight work, daily refresh, and in-memory request throttles. Restoring
the VM does not fix an independent managed-service outage or expired upstream
API quota. The managed services continue billing while the VM is stopped.
Retain the existing $50 project budget and alerts; alerts are notifications,
not spending caps. Cloud SQL shared-core compute is listed at $0.0105/hour,
about $7.67 for 730 hours, before storage, backups, networking, VM and other
charges or credits. Review current billing rather than assuming zero spending.

Sources: https://cloud.google.com/sql/pricing ;
https://github.com/GoogleCloudPlatform/cloud-sql-python-connector ;
https://docs.cloud.google.com/secret-manager/docs/authentication .
