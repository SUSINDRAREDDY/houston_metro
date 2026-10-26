# MetroAI Milestone 5 submission

Project: `metroai-vm-milestone-20260922`
Cluster: `metroai-gke`, `us-central1`
Hostname: https://metroai.136.81.119.160.sslip.io
Repository: https://github.com/SUSINDRAREDDY/houston_metro/tree/codex/milestone5-orchestration

## Prepared files

- `MetroAI_Milestone5_Two_Slides_Final.pptx`: exactly two editable slides.
- `Written_Analysis.pdf`: half-page discussion, on one letter-size page.
- `Written_Analysis.md`: editable analysis source.
- `evidence/pods-before-deletion.txt` and `pods-after-deletion.txt`: real rehearsal outputs.
- `evidence/replacement-events.txt` and `deleted-pod.txt`: deleted pod and replacement events.
- `evidence/hpa-before-load.yaml`, `hpa-during-load.yaml`, `hpa-after-load.yaml`:
  scaling snapshots; HPA events show 2 -> 3 -> 4 replicas under HTTP load.
- `evidence/load-test-results.json`: 35,715 HTTP 200 responses over 180.48 seconds.
- `evidence/scaling-observations.jsonl`: timestamped HPA telemetry.
- `evidence/final-two-replicas.txt`: healthy replicas after automatic scale-down.
- `evidence/http-redirect.txt`: server HTTP 301 and HTTPS Location header.
- Root repository `k8s/`: Deployment, Service, ingress, HPA, PDB, certificate,
  load balancer configuration, identity, nonsecret configuration and refresh jobs.
- `docs/MILESTONE5_RECORDING.md`: timed recording plan and exact demo commands.

## Remaining verification / human submission

The Google-managed certificate is ACTIVE in Google Cloud; the required screenshot
is `evidence/certificate-active.jpg`. The Kubernetes ManagedCertificate status may
lag behind the Compute certificate. Public TLS serving was still propagating at
the last check, so HTTPS is not yet declared verified. Background monitoring will
append end-to-end TLS evidence and a browser screenshot when serving succeeds.

Record the full 10-minute video with cameras on. Delete a pod LIVE during the video;
the saved rehearsal evidence is supplementary. Demonstrate actual HPA scaling,
valid HTTPS, HTTP redirection, and explain both slides. Then upload to OneDrive,
grant the three instructors access and submit its link in Canvas. These files do
not include a recorded video or a OneDrive submission.

Use the live repository branch above; its manifests and runtime changes are committed.
The original VM remains healthy for Milestone 4, with background refresh disabled
because Kubernetes CronJobs now perform that work. This does not make the zonal
Cloud SQL database highly available. No domain was purchased; sslip.io supplies DNS.
