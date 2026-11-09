# MetroAI Milestone 6 recording

Deployment branch: `codex/milestone6-observability`

[Live MetroAI](https://metroai.136.81.119.160.sslip.io/) · [GitHub Actions](https://github.com/SUSINDRAREDDY/houston_metro/actions/workflows/deploy.yml) · [Dashboard](https://console.cloud.google.com/monitoring/dashboards/builder/013313c3-d6c7-4f1d-a054-e161602a0d8a?project=metroai-vm-milestone-20260922) · [Alert policy](https://console.cloud.google.com/monitoring/alerting/policies/8599975247090027730?project=metroai-vm-milestone-20260922)

## Record on the machine that holds the Terraform state

1. Keep the presenters' cameras visible. Open the app and try its stop search.
2. Start a successful release early while you present monitoring and Terraform.

   ```bash
   git commit --allow-empty -m "Milestone 6 live deployment demo"
   git push
   ```

3. Generate five HTTP 503s from inside a pod and copy a request ID from the output.

   ```bash
   ./scripts/milestone6/demo-503.sh
   ```

   In [Logs Explorer](https://console.cloud.google.com/logs/query?project=metroai-vm-milestone-20260922), use this query. Expand a JSON record and match its request ID.

   ```text
   resource.type="k8s_container"
   resource.labels.cluster_name="metroai-gke"
   resource.labels.namespace_name="metroai"
   resource.labels.container_name="app"
   log_id("stdout")
   jsonPayload.event="http_request"
   jsonPayload.route="/api/internal/demo-503"
   jsonPayload.status_code=503
   ```

4. Run the refresh-enabled live Terraform plan while monitoring data arrives.

   ```bash
   ./scripts/milestone6/plan.sh
   ```

   Point out `No changes`. [Terraform coverage](../terraform/README.md) explains which systems own the remaining resources.

5. Show the error chart and CPU and memory charts. Open the policy and show the
   received alert. Use a rehearsal receipt when the opening notification has
   already been sent. Cloud Monitoring can take several minutes to ingest the
   burst and evaluate the threshold.
6. Show the successful Actions run and its public build SHA. Capture this SHA
   before pushing the controlled failure.

   ```bash
   curl -fsS https://metroai.136.81.119.160.sslip.io/api/version; echo
   ```

7. Trigger the bad rollout only after the successful run is complete.

   ```bash
   touch deploy/milestone6-fail-readiness
   git add deploy/milestone6-fail-readiness
   git commit -m "Milestone 6 live rollback demo"
   git push
   ```

   Show Actions building the candidate. GKE keeps healthy pods serving while
   the candidate fails readiness. After the workflow times out, show the
   automatic rollback lines. The run is marked failed because it rejected
   the release. Verify the earlier SHA and healthy readiness over HTTPS.

   ```bash
   curl -fsS https://metroai.136.81.119.160.sslip.io/api/health/ready; echo
   curl -fsS https://metroai.136.81.119.160.sslip.io/api/version; echo
   ```

8. After the failed run finishes, remove the demonstration marker and push a
   healthy commit. Wait for the workflow to pass and verify the site again.

   ```bash
   git rm deploy/milestone6-fail-readiness
   git commit -m "Clear Milestone 6 demo failure marker"
   git push
   ```

Capture the dashboard and alert policy in the Cloud Console and crop the
received notification to its title and timestamp. Save the two live run URLs
and commit SHAs for submission. Keep credentials, private state, and personal
mail off camera.
