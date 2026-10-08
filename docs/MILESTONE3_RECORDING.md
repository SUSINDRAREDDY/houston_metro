# Milestone 3 - 10-minute recording flow

Keep every presenting team member's camera visible during their portion. Run commands live and wait for each result. Use Chrome signed in as susindrar873@gmail.com for Google Cloud. Do not record an empty, loading, or error registry screen.

## 0:00-0:45 - Introduction and slide 1

Say: "We are demonstrating MetroAI running locally and on our Milestone 2 VM using the same Docker image. Our app service contains FastAPI and the static frontend. SQLite is stored in the metro-data volume. The container listens on port 8000; our laptop publishes port 8080 and our VM publishes port 8000."

## 0:45-2:45 - Local Docker Compose and full application

In Mac Terminal:

```bash
cd "/Users/sunny/Documents/ChatGPT/houston_metro 2"
export METRO_IMAGE="us-central1-docker.pkg.dev/metroai-vm-milestone-20260922/metroai/metroai@sha256:a8225a9f556231b7678572d659cdade4d287ee2f04b7a2191548483d0436fd10"
docker compose up -d --no-build
docker compose ps
curl --retry 10 --retry-all-errors --retry-delay 2 -fsS http://localhost:8080/api/status
```

Open http://localhost:8080/. Click UH -> Downtown and wait for journey results. Show the route map, Routes, and Service alerts. Allow enough time for external API responses.

Say: "Docker Compose starts our packaged application. Our transit database is ready, and we can plan this trip, view routes, and check service alerts."

## 2:45-4:00 - Live Artifact Registry, v1 and digest

Open https://console.cloud.google.com/artifacts?project=metroai-vm-milestone-20260922.

Click repository metroai, image metroai, then the digest tagged v1. Show the Overview with the full Digest and Tags: v1 visible together. This is the exact live page required by the TA, in addition to the separate screenshot.

In Mac Terminal:

```bash
gcloud artifacts docker images describe \
  us-central1-docker.pkg.dev/metroai-vm-milestone-20260922/metroai/metroai:v1 \
  --format="value(image_summary.digest)"
docker inspect houston_metro2-app-1 --format '{{.Image}}'
```

Say: "Here is our published v1 image in Artifact Registry. This digest identifies the artifact. We will pull this exact digest on the VM."

## 4:00-6:45 - SSH, pull and run on the VM

In Mac Terminal, refresh the VM's short-lived registry login without displaying the access token:

```bash
gcloud auth print-access-token | \
gcloud compute ssh metroai-vm \
  --project=metroai-vm-milestone-20260922 --zone=us-central1-a \
  --command="sudo docker login --username oauth2accesstoken --password-stdin us-central1-docker.pkg.dev" \
  -- -T
gcloud compute ssh metroai-vm \
  --project=metroai-vm-milestone-20260922 --zone=us-central1-a
```

Inside the VM:

```bash
cd /home/sunny/metroai
export METRO_IMAGE="us-central1-docker.pkg.dev/metroai-vm-milestone-20260922/metroai/metroai@sha256:a8225a9f556231b7678572d659cdade4d287ee2f04b7a2191548483d0436fd10"
sudo docker pull "$METRO_IMAGE"
sudo env METRO_HTTP_PORT=8000 METRO_IMAGE="$METRO_IMAGE" \
  docker compose -f docker-compose.milestone3.yml up -d --no-build
sudo docker compose -f docker-compose.milestone3.yml ps
sudo docker inspect metroai-app-1 --format '{{.Image}}'
curl --retry 10 --retry-all-errors --retry-delay 2 -fsS http://localhost:8000/api/status
```

Show http://35.202.153.219:8000/ in the browser and plan the same trip. If pull reports "Image is up to date", the pull succeeded and the exact image was already cached.

Say: "The VM pulls the same digest and runs it without reinstalling Python or rebuilding the frontend. The application works at our Milestone 2 URL."

## 6:45-8:00 - Budget and current spending

Show Billing -> Budgets & caps -> MetroAI VM Milestone. Show the $50 monthly amount, the project scope, all services, thresholds 10/20/25/50/100, and email notifications. Show current spending in the project budget/report.

Say: "Our monthly project budget is $50. We have all the alert thresholds from both lists in the assignment. These are email alerts, not an automatic spending cap. We also check current spending."

## 8:00-9:15 - Slide 2, image size, exclusions and secret verification

Show slide 2, then the committed Dockerfile and .dockerignore on GitHub, and the half-page written analysis.

Say: "Previously we copied code, installed dependencies, and started Python manually. Now we pull one tested image and start it with Compose. Our multi-stage build keeps Node build dependencies out of the final Python slim image. Docker reports 297.3 MB locally, while the compressed registry image is 69.9 MB. Our ignore file excludes secrets, environments, transit data, and generated frontend files. We checked all ten image layers for our three runtime credentials and found no matches."

## 9:15-10:00 - Submission artifacts

Show https://github.com/SUSINDRAREDDY/houston_metro with Dockerfile, docker-compose.yml, .dockerignore, the written analysis, and verification script. Show the registry screenshot and saved VM pull/run output.

Say: "Our repository includes the required container files. We have included the v1 registry screenshot, VM pull/run output, two slides, and written analysis. Both deployments use the same published digest."

## Submit after recording

Upload the full camera-on video to OneDrive. Share view or edit access with sdesini@cougarnet.uh.edu, krajan@cougarnet.uh.edu, and skolanu@cougarnet.uh.edu. Submit its shareable OneDrive link in Canvas, together with the required artifacts. Do not upload the video file directly to Canvas.
