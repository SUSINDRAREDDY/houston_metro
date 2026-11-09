# MetroAI infrastructure

This root describes the live Milestone 6 environment in GCP project
`metroai-vm-milestone-20260922`. Existing resources were adopted using the
import blocks. The Google provider is pinned by the lock file.

Terraform owns the GKE Autopilot cluster, app VPC and subnet, Cloud SQL private
service connection and reserved range, SQL instance and app database, web
static IP, private uploads bucket, Artifact Registry repository, Secret Manager
containers, runtime and CI service accounts and their app-specific IAM grants,
GitHub OIDC federation, the HTTP 5xx metric, dashboard, alert, and email channel.

Kubernetes manifests and GitHub Actions own Kubernetes workloads and the
deployed image. GKE controllers own the load balancer, managed certificate
provisioning, and Autopilot nodes. Database users and data, secret values and
versions, project billing and existing budget policies, enabled APIs and
Google-managed service agents are administered separately. The previous VM
and the default network are outside this GKE application's Terraform scope.
The cluster lifecycle ignores only the Autopilot privileged-admission field,
for which the provider proposes a wildcard when the API returns an empty
list. The live setting was preserved.

The private state and local alert email variable are intentionally gitignored.
Use the existing initialized checkout and run `scripts/milestone6/plan.sh`
to refresh against GCP. A fresh clone needs authorized access to the private
state and email variable. Do not initialize a second independent state against
this deployment.

On initial adoption, review the import plan before applying. If Cloud Monitoring
has just registered the counter, allow its descriptor to propagate before
creating the metric alert policy.
