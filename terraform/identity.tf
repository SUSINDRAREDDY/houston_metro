locals {
  project         = "metroai-vm-milestone-20260922"
  project_number  = "1065898950357"
  runtime_member  = "serviceAccount:${google_service_account.runtime.email}"
  deployer_member = "serviceAccount:${google_service_account.deployer.email}"
  github_repo_id  = "1367503643"
  github_owner_id = "126981466"
  deploy_ref      = "refs/heads/codex/milestone6-observability"
  deploy_workflow = "SUSINDRAREDDY/houston_metro/.github/workflows/deploy.yml"
}

resource "google_project_iam_member" "runtime_cloudsql" {
  project = local.project
  role    = "roles/cloudsql.client"
  member  = local.runtime_member
}

resource "google_service_account_iam_member" "runtime_gke" {
  service_account_id = google_service_account.runtime.name
  role               = "roles/iam.workloadIdentityUser"
  member             = "serviceAccount:${local.project}.svc.id.goog[metroai/metroai-app]"
}

resource "google_storage_bucket_iam_member" "runtime_uploads" {
  bucket = google_storage_bucket.uploads.name
  role   = "roles/storage.objectUser"
  member = local.runtime_member
}

resource "google_secret_manager_secret_iam_member" "runtime_secrets" {
  for_each = {
    db_password          = google_secret_manager_secret.db_password.secret_id
    metro_api_key        = google_secret_manager_secret.metro_api_key.secret_id
    openrouter_api_key   = google_secret_manager_secret.openrouter_api_key.secret_id
    transit_data_api_key = google_secret_manager_secret.transit_data_api_key.secret_id
  }

  project   = local.project
  secret_id = each.value
  role      = "roles/secretmanager.secretAccessor"
  member    = local.runtime_member
}

resource "google_artifact_registry_repository_iam_member" "image_readers" {
  for_each = {
    nodes   = "serviceAccount:${local.project_number}-compute@developer.gserviceaccount.com"
    runtime = local.runtime_member
  }

  project    = local.project
  location   = google_artifact_registry_repository.metroai.location
  repository = google_artifact_registry_repository.metroai.repository_id
  role       = "roles/artifactregistry.reader"
  member     = each.value
}

resource "google_service_account" "deployer" {
  account_id   = "metroai-m6-deploy"
  display_name = "MetroAI GitHub deployment"
}

resource "google_iam_workload_identity_pool" "github" {
  workload_identity_pool_id = "metroai-github"
  display_name              = "MetroAI GitHub Actions"
}

resource "google_iam_workload_identity_pool_provider" "github" {
  workload_identity_pool_id          = google_iam_workload_identity_pool.github.workload_identity_pool_id
  workload_identity_pool_provider_id = "github"
  attribute_mapping = {
    "google.subject"          = "assertion.sub"
    "attribute.repository_id" = "assertion.repository_id"
  }
  attribute_condition = join(" && ", [
    "assertion.repository_owner_id == '${local.github_owner_id}'",
    "assertion.repository_id == '${local.github_repo_id}'",
    "assertion.ref == '${local.deploy_ref}'",
    "assertion.workflow_ref == '${local.deploy_workflow}@${local.deploy_ref}'",
  ])

  oidc {
    issuer_uri = "https://token.actions.githubusercontent.com"
  }
}

resource "google_service_account_iam_member" "github_deployer" {
  service_account_id = google_service_account.deployer.name
  role               = "roles/iam.workloadIdentityUser"
  member             = "principalSet://iam.googleapis.com/${google_iam_workload_identity_pool.github.name}/attribute.repository_id/${local.github_repo_id}"
}

resource "google_project_iam_member" "deployer_cluster" {
  project = local.project
  role    = "roles/container.clusterViewer"
  member  = local.deployer_member
}

resource "google_artifact_registry_repository_iam_member" "deployer_images" {
  project    = local.project
  location   = google_artifact_registry_repository.metroai.location
  repository = google_artifact_registry_repository.metroai.repository_id
  role       = "roles/artifactregistry.writer"
  member     = local.deployer_member
}
