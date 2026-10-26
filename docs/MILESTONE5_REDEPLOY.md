# Restart the prepared Milestone 5 demo

The cluster, namespace, identities, private database networking, Service, ingress,
load balancer, static IP, managed certificate, PDB, configuration and refresh
CronJobs are retained. The web Deployment and HPA have been removed for a clean
redeployment demonstration. The old demo load Job has also been removed.
The public GKE website has no serving application until the Deployment is reapplied.

In the existing Cloud Shell:

```bash
cd ~/metroai-milestone5
kubectl apply -f k8s/
kubectl get pods -n metroai -l app=metroai -w
```

Wait for two pods to show 1/1 Ready and Running. Press Ctrl+C to stop the watch.
Pod readiness and load balancer backend readiness may take time to propagate.
If Autopilot removed idle nodes, it provisions nodes again automatically.

Verify the retained HTTPS address:

```bash
curl -I https://metroai.136.81.119.160.sslip.io/
```

A ready application should return HTTP 200. Then follow MILESTONE5_RECORDING.md
for the live deletion, autoscaling, HTTPS, probe and submission demonstrations.
No image build, cluster creation, IAM setup, IP allocation or certificate creation
is needed. Applying the root k8s directory does not start the demo load Job in
k8s/demo/. The refresh CronJobs continue keeping the shared database current.

The retained cluster/load balancer/static IP and managed services may still bill
while application pods are absent; this reset does not tear down infrastructure.
