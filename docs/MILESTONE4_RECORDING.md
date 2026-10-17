# Milestone 4: 10-minute recording flow

Keep every presenter's face visible during their speaking portion. Open the
two slides, app, Cloud SQL, bucket, IAM, Secret Manager, and this branch on
GitHub before recording. Keep secret values and `.env` contents off screen.
If the app cannot be reached after changing networks, update its presenter-only
firewall source IP before recording. Do not open the database to public IP.

## 0:00-1:00 - Slide 1: where state lives

Show slide 1.

Say: "Our project is MetroAI. In Milestone 3, our database was SQLite in a Docker
volume, and our API keys came from a local environment file. For Milestone 4,
we moved transit data and saved alert state to Cloud SQL, files to Cloud Storage,
and credentials to Secret Manager. Our VM now runs the application without a
persistent data volume."

## 1:00-3:00 - Working application and managed database

Open http://35.202.153.219:8000/. Show routes, stop search, and a UH-to-Downtown
journey. Disable "Include walking connections" for the timetable search: this
proves the managed database supplies the journey, rather than relying on the
external METRO planner. Choose a reasonable upcoming daytime departure if
current service is sparse. Current coverage appears in `/api/status`.

Mac terminal:

```bash
curl -fsS http://35.202.153.219:8000/api/status

gcloud sql instances describe metroai-postgres \
  --project=metroai-vm-milestone-20260922 \
  --format='yaml(state,ipAddresses,settings.ipConfiguration)'
```

Show the Cloud SQL connection configuration: private IP `10.164.0.3`, public
IP disabled, associated VPC `metroai-vpc`.

Say: "The app is reading the managed PostgreSQL database. This instance has
only a private IP and no public IP. Our VM reaches it through our private VPC
using the Cloud SQL connector."

## 3:00-4:15 - Migration and matching row counts

Show the committed `migrations/001_managed_state.sql` on the `codex/milestone4-state`
branch. Scroll through the real CREATE TABLE statements. Show
`deliverables/milestone4/Row_Counts.csv` or the matching rows in the evidence PDF.

Say: "We created these tables using this migration file, then copied a consistent
snapshot of our old database. The old and new row counts match for every source
table, including stops, routes, trips, stop times, shapes, and our separate GIS
reference data. We retained the original snapshot in private storage."

## 4:15-6:00 - Upload a file through the application

In the app, open Files. Select `MetroAI_Trip_Note.txt` from the submission
folder, click Upload file, and show the saved filename. Download it once to
show it can be retrieved. The file is a harmless demo note, not a secret.

Open the bucket, refresh, and navigate into `uploads/`, then the newest UUID
folder. Show the exact filename uploaded through the app. Do not upload directly
through the Cloud Console as a substitute for the app demonstration.

Say: "This file was uploaded through MetroAI and is now in Cloud Storage. Its
metadata is in PostgreSQL. The application uses the VM's attached service
account, not a downloaded JSON key. The bucket is private."

## 6:00-7:30 - Identity and networking, slide 2

Show slide 2 and the IAM screenshots. Show the service account email attached
to the VM. Show resource-specific grants on the bucket and secrets as well as
Cloud SQL Client on the project. These grants have different scopes; the
project IAM table alone does not list every resource-specific grant.

Mac terminal, if needed:

```bash
gcloud compute instances describe metroai-vm \
  --zone=us-central1-a --project=metroai-vm-milestone-20260922 \
  --format='yaml(serviceAccounts,networkInterfaces[0].subnetwork)'

gcloud iam service-accounts keys list \
  --iam-account=metroai-runtime@metroai-vm-milestone-20260922.iam.gserviceaccount.com \
  --project=metroai-vm-milestone-20260922 --managed-by=user
```

The user-managed key list should be empty. Google-managed internal keys do not
mean a downloaded JSON key exists.

Say: "Our runtime identity has Cloud SQL Client, Storage Object User on our
bucket, Secret Accessor on four runtime secrets, and Registry Reader on our image
repository. The database is private. Only the application has a public VM
address, restricted to our presenter IP."

## 7:30-8:45 - No environment file, secrets manager names

SSH from Mac:

```bash
gcloud compute ssh sunny@metroai-vm \
  --project=metroai-vm-milestone-20260922 --zone=us-central1-a
```

Run inside the VM:

```bash
sudo docker exec metroai-m4-app-1 sh -c \
  'if find /app /home /tmp -type f -name ".env*" 2>/dev/null | grep -q .; then echo "FAIL: environment file found"; exit 1; else echo "PASS: no .env file in container"; fi'

sudo docker inspect metroai-m4-app-1 \
  --format 'Read-only filesystem: {{.HostConfig.ReadonlyRootfs}} | Data mounts: {{json .Mounts}}'
```

Open Secret Manager and show only the list of names. Do not click "View secret
value" or run commands that print secret contents.

Say: "There is no environment file inside our container. Credentials are read
from Secret Manager into memory using the VM's identity. These are the secret
names; their values remain hidden."

## 8:45-10:00 - What survives, written analysis, artifacts

Show the one-page written analysis and submission files.

Say: "If our VM were deleted now, the website and active requests would stop.
Our daily refresh would pause, and in-memory request state would be lost. Our
database, uploads, secrets, published image, network, service account, and
reserved IP would survive. We can create a replacement VM, attach the same
identity, and run our saved startup script. Recovery still needs an operator;
we are not claiming automatic failover. We tested container recreation without
deleting the VM. Managed resources continue billing during downtime, so we
retain our budget alerts and monitor spending."

Show the repository branch link and the migration, matching row counts, private
database screenshot, IAM bindings, and Secret Manager screenshot.

## Submit

Upload the full camera-on video to OneDrive. Give view or edit access to
`sdesini@cougarnet.uh.edu`, `krajan@cougarnet.uh.edu`, and
`skolanu@cougarnet.uh.edu`. Submit the OneDrive share link in Canvas, not a direct
video upload. Include the two-slide PowerPoint, one-page analysis, repository
branch link, migration, row-count evidence, and required screenshots.

Console links:

- Cloud SQL: https://console.cloud.google.com/sql/instances/metroai-postgres/overview?project=metroai-vm-milestone-20260922
- Bucket: https://console.cloud.google.com/storage/browser/metroai-vm-milestone-20260922-uploads?project=metroai-vm-milestone-20260922
- IAM: https://console.cloud.google.com/iam-admin/iam?project=metroai-vm-milestone-20260922
- Secrets: https://console.cloud.google.com/security/secret-manager?project=metroai-vm-milestone-20260922
- Repository: https://github.com/SUSINDRAREDDY/houston_metro/tree/codex/milestone4-state
