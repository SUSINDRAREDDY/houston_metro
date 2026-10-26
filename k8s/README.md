# MetroAI Milestone 5

Project `metroai-vm-milestone-20260922`, cluster `metroai-gke`, region `us-central1`.
Application: https://metroai.136.81.119.160.sslip.io
Global static IP: `metroai-gke-ip` (`136.81.119.160`).

The `sslip.io` DNS service supplies the real hostname without purchasing a domain;
Google provisions the certificate separately. Do not treat the app as HTTPS-ready
until ManagedCertificate reports Active and a TLS client verifies the hostname.
The hostname depends on this static IP and the third-party DNS service.

## Apply

Authenticate to the correct cluster before applying:

```sh
gcloud container clusters get-credentials metroai-gke --region=us-central1 --project=metroai-vm-milestone-20260922
kubectl config current-context
kubectl apply -f k8s/
```

The root directory includes only steady-state resources. The bounded load-test
Job is in `demo/` and is not applied by the command above. Reapplying deployment.yaml
sets replicas to its declared 2; avoid doing that during a scaling demonstration.

## Identity and networking

The cluster uses `metroai-vpc` / `metroai-subnet`, which reaches private Cloud SQL
`10.164.0.3`. Kubernetes account `metroai/metroai-app` impersonates
`metroai-runtime@metroai-vm-milestone-20260922.iam.gserviceaccount.com`.
That account retains the Milestone 4 Cloud SQL, Storage, and per-secret roles.
The IAM binding outside Kubernetes is:

```sh
gcloud iam service-accounts add-iam-policy-binding metroai-runtime@metroai-vm-milestone-20260922.iam.gserviceaccount.com --project=metroai-vm-milestone-20260922 --role=roles/iam.workloadIdentityUser --member='serviceAccount:metroai-vm-milestone-20260922.svc.id.goog[metroai/metroai-app]'
gcloud artifacts repositories add-iam-policy-binding metroai --location=us-central1 --project=metroai-vm-milestone-20260922 --member='serviceAccount:1065898950357-compute@developer.gserviceaccount.com' --role=roles/artifactregistry.reader
```

No secret values or service-account keys are in these manifests. The node identity
pulls the image; the pod identity reads managed application resources.

## Runtime

The image combines Next.js static assets and FastAPI on port 8000. Service port 80
routes to the named container port `http`. GKE ingress configures the external
Application Load Balancer and its pod network endpoint groups (NEGs).

- Startup/liveness: `/api/health/live`, no dependency queries.
- Readiness and LB health: `/api/health/ready`, PostgreSQL transit-data query; 503 on failure.
- HPA: CPU target 60% of each 500m CPU request, minimum 2, maximum 4 replicas.
- PDB: at least 1 available during supported voluntary evictions.
- Rolling updates: maxUnavailable 0, maxSurge 1.
- Read-only root filesystem, numeric non-root UID 1000, disposable `/tmp` volume.
- Pre-stop delay and termination grace allow endpoint removal and request draining.
- Topology spread is a preference, not a guarantee of different nodes or zones.

`BACKGROUND_REFRESH_ENABLED=false` prevents refresh loops in each web replica.
CronJobs refresh alerts every five minutes and GTFS daily at 03:00 America/Chicago;
concurrencyPolicy Forbid prevents overlap within each CronJob. The feed refresher
also uses the application's PostgreSQL advisory lock. Disable the old VM's refresh
loops after verifying the CronJob handoff; the VM is retained for Milestone 4.

## Evidence and bounded load

```sh
kubectl get pods -n metroai -o wide
kubectl get managedcertificate metroai-certificate -n metroai
kubectl get hpa metroai -n metroai
kubectl get pdb metroai -n metroai
kubectl apply -f k8s/demo/load-test.yaml
kubectl get hpa metroai -n metroai -w
```

The load Job makes actual GET requests to the app homepage for 60 seconds.
It does not call the AI provider, write application data, or set replica counts.
Remove the completed Job before repeating: `kubectl delete job metroai-load-test -n metroai`.
Save HPA events and pod output during the run. A running Job alone is not proof
of scaling: verify `SuccessfulRescale` and a changed Deployment replica count.

The certificate and HTTP redirect are separate checks. FrontendConfig retains an
HTTP listener to return a redirect to HTTPS. Do not disable ingress HTTP.

## Limits and cleanup

The database is the existing zonal shared-core instance, not an HA database.
Extra web replicas do not make database or upstream METRO/API outages disappear.
There is no user authentication; the public endpoint is a limited coursework demo.
GKE workloads, the load balancer and managed services incur charges while present.
After grading, delete the demo load Job, ingress and cluster only when no longer
needed, and release the global IP. Preserve the Milestone 4 database/bucket unless
explicitly retiring that milestone as well.

Sources: https://docs.cloud.google.com/kubernetes-engine/docs/how-to/ingress-configuration
https://docs.cloud.google.com/kubernetes-engine/docs/concepts/workload-identity
https://kubernetes.io/docs/concepts/workloads/pods/disruptions/
https://nip.io/
