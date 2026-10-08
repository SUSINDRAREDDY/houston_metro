# Milestone 3 - Written Analysis

Our v1 image reports **297,289,101 bytes (297.3 MB)** in local Docker; its compressed AMD64 image in Artifact Registry is **69,889,276 bytes (69.9 MB)**. We use a multi-stage Dockerfile: Node builds the frontend, while our Python slim runtime receives only the exported static files. This removes Node, npm, and frontend build dependencies from the runtime. `pip install --no-cache-dir` also avoids retained download caches.

Our `.dockerignore` excludes `.env` and `.env.*` to protect credentials; `.git` to remove repository history; `.venv` to exclude machine-specific dependencies; and `data` because the transit database belongs in a persistent volume. We exclude `frontend/node_modules`, `frontend/.next`, and `frontend/out` because Docker rebuilds the frontend, and `__pycache__` because Python can regenerate bytecode. These exclusions keep unnecessary local files out of the build context.

We pass API keys through runtime environment variables. We checked the exported image configuration, build history, and all **ten decompressed layers** against our **three current runtime credentials**. We found **zero credential matches, zero .env files, and no embedded application credential variables**. Our repository includes the verification script; its results apply to the credentials checked.

For cost control, we reuse our **e2-small VM** and maintain a **$50 monthly project budget** with email alerts at **10%, 20%, 25%, 50%, and 100%**, covering both assignment lists. The October 8 budget view showed **$0.00 net spending with $3.07 savings**. We monitor the project budget and spending; credits explain the zero net amount. Email alerts do not automatically stop the VM.
