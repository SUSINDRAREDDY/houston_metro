# MetroAI: availability and PodDisruptionBudget

Without a PodDisruptionBudget (PDB), concurrent voluntary evictions during node
maintenance can remove every ready application replica. The load balancer then
has no healthy destination, causing intermittent 5xx responses until replacement
pods become ready. Terminating backends can also interrupt in-flight requests.
Missing a PDB does not itself cause an error; a disruption must remove too much
serving capacity.

MetroAI uses at least two GKE replicas and a PDB with minAvailable: 1, limiting
supported voluntary evictions to preserve one available replica. Rolling updates
are separately configured with maxUnavailable: 0 and maxSurge: 1. Readiness queries
PostgreSQL transit data and returns 503 when unavailable; application-only liveness
avoids database-triggered restart loops. The load balancer checks readiness too.
Connection draining, a pre-stop delay and a termination grace period reduce
interruption while endpoints are removed.

Our bounded HTTP test triggered actual HPA scaling from two to three and then four
replicas; all 35,715 responses were HTTP 200. A separate deletion rehearsal showed
automatic pod replacement. These observations do not prove the PDB prevented an
outage: direct pod deletion bypasses PDBs, and PDBs do not govern Deployment rolling
updates or prevent node crashes. The live deletion demo demonstrates controller
replacement, not PDB enforcement. We did not deliberately remove all serving
capacity or disable the PDB to manufacture errors. The existing zonal database,
shared dependencies and pods placed on one node remain availability limits even
with multiple replicas.

Sources: https://kubernetes.io/docs/concepts/workloads/pods/disruptions/
https://docs.cloud.google.com/kubernetes-engine/docs/how-to/ingress-configuration
