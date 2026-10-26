# MetroAI Milestone 5: 10-minute recording

Every presenter must show their face during their portion. Keep a camera overlay
visible beside the terminal/browser. This is a recording plan, not a claim that a
video has been recorded. Rehearsal evidence cannot replace the live pod-deletion demo.

## 0:00-1:00: application and topology

Open https://metroai.136.81.119.160.sslip.io after certificate verification succeeds.
Show the transit app, choose UH and Downtown, and search a valid future departure.
Use slide 1 to explain GKE, ingress/load balancer, Service, replicas, private Cloud
SQL and Storage. Ingress is configuration; the Google load balancer uses pod NEGs.

## 1:00-2:00: healthy replicas

Run in Cloud Shell connected to this project's cluster:

```bash
kubectl get pods -n metroai -l app=metroai -o wide
kubectl get deployment metroai -n metroai
kubectl get hpa,pdb -n metroai
```

Confirm at least two application pods are Ready. Completed refresh/load Jobs are
not application replicas. Explain that the database and uploads are shared managed
services, not local pod data.

## 2:00-3:30: delete and replace LIVE

First save the before output. Select one current pod, using its real name:

```bash
mkdir -p evidence
kubectl get pods -n metroai -o wide | tee evidence/pods-before-deletion.txt
kubectl get pods -n metroai -l app=metroai
kubectl delete pod REAL_POD_NAME -n metroai --wait=false
kubectl get pods -n metroai -l app=metroai -w
```

Wait for the newly named pod to be Ready, then Ctrl+C stops the watch only.

```bash
kubectl get pods -n metroai -o wide | tee evidence/pods-after-deletion.txt
```

Explain that the Deployment/ReplicaSet replaces the deleted pod. The PDB does not
block this direct deletion; its role concerns voluntary evictions via the Eviction API.

## 3:30-6:30: actual autoscaling

Use a checkout containing the committed `k8s/` directory. The load test is bounded
to three minutes and requests only the app homepage. It does not call AI services.

```bash
kubectl delete job metroai-load-test -n metroai --ignore-not-found
kubectl apply -f k8s/demo/load-test.yaml
kubectl get hpa metroai -n metroai -w
```

Use another Cloud Shell terminal to show:

```bash
kubectl get pods -n metroai -l app=metroai -w
```

Capture actual changed replica counts and `SuccessfulRescale` evidence:

```bash
kubectl describe hpa metroai -n metroai
kubectl logs job/metroai-load-test -n metroai
```

Do not use `kubectl scale` as proof of autoscaling. Rehearsal observed 2 -> 3 -> 4.
The HPA later reduces replicas to its minimum as measured CPU falls. If still at
four from a previous rehearsal, wait for scale-down before starting the recording.

## 6:30-8:00: HTTPS, certificate and redirect

In the browser, open the HTTPS address. Open the site security information and
certificate details to show a valid certificate matching the hostname. Modern
browsers can use a site-controls icon instead of a literal padlock.

```bash
gcloud compute ssl-certificates describe mcrt-0a2e9654-8f55-4313-b784-c9e6deca852b --project=metroai-vm-milestone-20260922 --format="yaml(managed.status,managed.domainStatus)"
curl -I http://metroai.136.81.119.160.sslip.io/
```

Capture the certificate status showing Active. Type the HTTP URL in the browser
and show it ends at HTTPS. A browser may upgrade HTTP before sending it, so the
curl result must also show the server's redirect and Location header.

## 8:00-10:00: probes, repository and conclusion

Use slide 2: liveness only checks application response, readiness checks PostgreSQL.
Show the committed Deployment, Service, ingress, HPA and PDB. Explain the written
analysis without claiming the PDB protects direct deletion or database failures.
Show the two named refresh CronJobs and the managed database/storage topology.

## Submit

Upload the complete video to OneDrive, share view or edit access with
sdesini@cougarnet.uh.edu, krajan@cougarnet.uh.edu, and skolanu@cougarnet.uh.edu.
Submit the shareable OneDrive link in Canvas, not the video file. Include the
two-slide PPTX, half-page analysis, Active certificate screenshot, pod outputs,
and accessible repository link containing committed manifests. Verify your
instructors can access the private GitHub repository and OneDrive folder.
