# MetroAI orchestration preparation

The existing Milestone 4 VM remains a single Docker Compose application. The GKE
deployment and remaining manifests are now in `k8s/`; see `k8s/README.md` and
`docs/MILESTONE5_RECORDING.md` for operations and the live recording. This file
preserves the preparation rationale; completion evidence is in deliverables/milestone5/.

## Container changes

- `/api/health/live`: HTTP 200 when the application serves requests; no database or upstream API calls.
- `/api/health/ready`: queries the transit database and requires a row in `stops`.
  Returns HTTP 503 on connection failure or missing transit data, without driver details.
- `/api/health`: retained for compatibility with the existing VM healthcheck.
- `BACKGROUND_REFRESH_ENABLED` defaults to `true`, preserving the VM refresh loops.
  Set it to `false` on GKE web pods, and arrange a single scheduled feed-refresh job
  (`python -m backend.managed_refresh`). Alerts must also have an external refresh
  mechanism before disabling the loops; run `python -c 'from backend import alerts; alerts.refresh()'`
  on a schedule or implement a dedicated refresh worker. The GKE CronJobs now handle
  both schedules; the old VM compose disables its loops after the alert job was verified.

## Guided next steps

1. Verify the updated VM first: `/api/health/live`, `/api/health/ready`, and a real journey.
2. Create GKE with connectivity to `metroai-vpc` and private Cloud SQL.
3. Configure Workload Identity for the existing runtime Google service account;
   preserve its restricted Secret Manager, Storage, and Cloud SQL permissions.
4. Deploy the new image by digest with two replicas and CPU/memory requests.
   Add startup, liveness and readiness probes. Allow startup enough time for database
   initialization. Probe timeouts must account for database connection latency.
5. Add Service, ingress, HPA and PDB (`minAvailable: 1`). Configure the load
   balancer's backend health check to use readiness on port 8000.
6. Configure hostname, managed certificate and HTTP redirect; verify Active.
7. Record live replacement, actual scaling, certificate and redirect evidence.

No cluster, load balancer or certificate is provisioned by these code changes.
