# MetroAI Milestone 5 submission

Project: `metroai-vm-milestone-20260922`
Cluster: `metroai-gke`, `us-central1`
Hostname: https://metroai.136.81.119.160.sslip.io
Repository: https://github.com/SUSINDRAREDDY/houston_metro/tree/codex/milestone5-orchestration

## Four-command recording option

Run these one at a time in the existing Cloud Shell; each command finishes before
the next. No manual deletion or load commands are needed in addition.

```bash
bash ~/metroai-milestone5/demo.sh 1
bash ~/metroai-milestone5/demo.sh 2
bash ~/metroai-milestone5/demo.sh 3
bash ~/metroai-milestone5/demo.sh 4
```

1 shows healthy replicas and starts a new evidence folder; 2 deletes one pod live
and waits for its replacement; 3 starts real bounded HTTP load and shows actual
HPA changes; 4 shows HTTP redirect, verified HTTPS, certificate status and both
probe responses. Output is live and evidence is saved across the four commands.

Keep the camera on. Separately show the app, both slides, browser security and
certificate details, the Google Cloud ACTIVE certificate page, browser HTTP
redirection, and committed manifests. The script does not replace those visual
requirements, the half-page analysis, or OneDrive upload/sharing/submission.

## Restart before recording

The web Deployment and HPA are currently removed for a clean redeploy.
The existing cluster, load balancer, certificate, identities and refresh CronJobs
are retained. In Cloud Shell run `cd ~/metroai-milestone5`, then
`kubectl apply -f k8s/`. Wait for two ready pods before starting the recording
or the guided helper. See `docs/MILESTONE5_REDEPLOY.md` in the repository.

## Record with one command

In your prepared Cloud Shell terminal run:

```bash
bash ~/metroai-milestone5/demo.sh
```

Press Enter at each stage. The helper performs real deletion/replacement and
HTTP-load autoscaling, saves new live evidence, and prompts you to show the browser,
slides, committed files and certificate. Keep your camera on. You still record the
video, show browser certificate security information, and submit via OneDrive.

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
is `evidence/certificate-active.jpg`. Public HTTPS now passes normal certificate
and hostname verification. The homepage, liveness, readiness, database status,
UH stop search and upload listing all returned HTTP 200; see
`evidence/public-https-verification.json`. Kubernetes ManagedCertificate status can
lag behind the Compute certificate. The HTTP 301 redirect is separately captured.

Record the full 10-minute video with cameras on. Delete a pod LIVE during the video;
the saved rehearsal evidence is supplementary. Demonstrate actual HPA scaling,
valid HTTPS, HTTP redirection, and explain both slides. Then upload to OneDrive,
grant the three instructors access and submit its link in Canvas. These files do
not include a recorded video or a OneDrive submission.

Use the live repository branch above; its manifests and runtime changes are committed.
The original VM remains healthy for Milestone 4, with background refresh disabled
because Kubernetes CronJobs now perform that work. This does not make the zonal
Cloud SQL database highly available. No domain was purchased; sslip.io supplies DNS.
