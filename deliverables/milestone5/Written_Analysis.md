# MetroAI: keeping the app available

During planned node maintenance, Kubernetes may remove application pods. Without a PodDisruptionBudget (PDB), several pods could be removed at the same time. If no ready pod remains, the load balancer has nowhere to send requests. Users may then see 5xx server errors until replacement pods are ready.

Our Houston Metro app runs at least two replicas on GKE. Our PDB uses `minAvailable: 1`. For maintenance that follows the PDB, Kubernetes must keep at least one available replica. We also configure rolling updates to keep the existing replicas available while a new pod starts. Readiness checks the database before a pod receives traffic. Liveness checks only the app, so a database outage does not repeatedly restart the containers.

Our earlier HTTP load test returned only successful responses, and our deletion test showed Kubernetes creating a replacement pod. However, this does not prove the PDB prevented an outage. Direct pod deletion bypasses the PDB. The PDB also cannot prevent a node crash or database outage. We did not remove the PDB to deliberately cause failures. These limits explain why multiple pods and a PDB improve availability but cannot prevent every interruption.

All five required manifests are committed: deployment, service, ingress, autoscaler (`hpa.yaml`), and PodDisruptionBudget (`pdb.yaml`).

[Open the committed manifests on GitHub](https://github.com/SUSINDRAREDDY/houston_metro/tree/codex/milestone5-orchestration/k8s)

Source: [Kubernetes documentation on disruptions and PDB limits](https://kubernetes.io/docs/concepts/workloads/pods/disruptions/)
