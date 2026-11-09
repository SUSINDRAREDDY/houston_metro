import {
  to = google_container_cluster.metroai
  id = "projects/metroai-vm-milestone-20260922/locations/us-central1/clusters/metroai-gke"
}

import {
  to = google_compute_network.metroai
  id = "projects/metroai-vm-milestone-20260922/global/networks/metroai-vpc"
}

import {
  to = google_compute_subnetwork.metroai
  id = "projects/metroai-vm-milestone-20260922/regions/us-central1/subnetworks/metroai-subnet"
}

import {
  to = google_compute_global_address.web
  id = "projects/metroai-vm-milestone-20260922/global/addresses/metroai-gke-ip"
}

import {
  to = google_compute_global_address.database
  id = "projects/metroai-vm-milestone-20260922/global/addresses/metroai-db-private-range"
}

import {
  to = google_service_networking_connection.database
  id = "projects/metroai-vm-milestone-20260922/global/networks/metroai-vpc:servicenetworking.googleapis.com"
}

import {
  to = google_sql_database_instance.metroai
  id = "projects/metroai-vm-milestone-20260922/instances/metroai-postgres"
}

import {
  to = google_sql_database.metroai
  id = "projects/metroai-vm-milestone-20260922/instances/metroai-postgres/databases/metroai"
}

import {
  to = google_storage_bucket.uploads
  id = "metroai-vm-milestone-20260922-uploads"
}

import {
  to = google_artifact_registry_repository.metroai
  id = "projects/metroai-vm-milestone-20260922/locations/us-central1/repositories/metroai"
}

import {
  to = google_service_account.runtime
  id = "projects/metroai-vm-milestone-20260922/serviceAccounts/metroai-runtime@metroai-vm-milestone-20260922.iam.gserviceaccount.com"
}

import {
  to = google_secret_manager_secret.db_admin_password
  id = "projects/metroai-vm-milestone-20260922/secrets/metroai-db-admin-password"
}

import {
  to = google_secret_manager_secret.db_password
  id = "projects/metroai-vm-milestone-20260922/secrets/metroai-db-password"
}

import {
  to = google_secret_manager_secret.metro_api_key
  id = "projects/metroai-vm-milestone-20260922/secrets/metroai-metro-api-key"
}

import {
  to = google_secret_manager_secret.openrouter_api_key
  id = "projects/metroai-vm-milestone-20260922/secrets/metroai-openrouter-api-key"
}

import {
  to = google_secret_manager_secret.transit_data_api_key
  id = "projects/metroai-vm-milestone-20260922/secrets/metroai-transit-data-api-key"
}

import {
  to = google_project_iam_member.runtime_cloudsql
  id = "metroai-vm-milestone-20260922 roles/cloudsql.client serviceAccount:metroai-runtime@metroai-vm-milestone-20260922.iam.gserviceaccount.com"
}

import {
  to = google_service_account_iam_member.runtime_gke
  id = "projects/metroai-vm-milestone-20260922/serviceAccounts/metroai-runtime@metroai-vm-milestone-20260922.iam.gserviceaccount.com roles/iam.workloadIdentityUser serviceAccount:metroai-vm-milestone-20260922.svc.id.goog[metroai/metroai-app]"
}

import {
  to = google_storage_bucket_iam_member.runtime_uploads
  id = "b/metroai-vm-milestone-20260922-uploads roles/storage.objectUser serviceAccount:metroai-runtime@metroai-vm-milestone-20260922.iam.gserviceaccount.com"
}

import {
  to = google_artifact_registry_repository_iam_member.image_readers["nodes"]
  id = "projects/metroai-vm-milestone-20260922/locations/us-central1/repositories/metroai roles/artifactregistry.reader serviceAccount:1065898950357-compute@developer.gserviceaccount.com"
}

import {
  to = google_artifact_registry_repository_iam_member.image_readers["runtime"]
  id = "projects/metroai-vm-milestone-20260922/locations/us-central1/repositories/metroai roles/artifactregistry.reader serviceAccount:metroai-runtime@metroai-vm-milestone-20260922.iam.gserviceaccount.com"
}

import {
  to = google_service_account.deployer
  id = "projects/metroai-vm-milestone-20260922/serviceAccounts/metroai-m6-deploy@metroai-vm-milestone-20260922.iam.gserviceaccount.com"
}

import {
  to = google_iam_workload_identity_pool.github
  id = "projects/metroai-vm-milestone-20260922/locations/global/workloadIdentityPools/metroai-github"
}

import {
  to = google_iam_workload_identity_pool_provider.github
  id = "projects/metroai-vm-milestone-20260922/locations/global/workloadIdentityPools/metroai-github/providers/github"
}

import {
  to = google_service_account_iam_member.github_deployer
  id = "projects/metroai-vm-milestone-20260922/serviceAccounts/metroai-m6-deploy@metroai-vm-milestone-20260922.iam.gserviceaccount.com roles/iam.workloadIdentityUser principalSet://iam.googleapis.com/projects/1065898950357/locations/global/workloadIdentityPools/metroai-github/attribute.repository_id/1367503643"
}

import {
  to = google_project_iam_member.deployer_cluster
  id = "metroai-vm-milestone-20260922 roles/container.clusterViewer serviceAccount:metroai-m6-deploy@metroai-vm-milestone-20260922.iam.gserviceaccount.com"
}

import {
  to = google_artifact_registry_repository_iam_member.deployer_images
  id = "projects/metroai-vm-milestone-20260922/locations/us-central1/repositories/metroai roles/artifactregistry.writer serviceAccount:metroai-m6-deploy@metroai-vm-milestone-20260922.iam.gserviceaccount.com"
}

import {
  to = google_secret_manager_secret_iam_member.runtime_secrets["db_password"]
  id = "projects/metroai-vm-milestone-20260922/secrets/metroai-db-password roles/secretmanager.secretAccessor serviceAccount:metroai-runtime@metroai-vm-milestone-20260922.iam.gserviceaccount.com"
}

import {
  to = google_secret_manager_secret_iam_member.runtime_secrets["metro_api_key"]
  id = "projects/metroai-vm-milestone-20260922/secrets/metroai-metro-api-key roles/secretmanager.secretAccessor serviceAccount:metroai-runtime@metroai-vm-milestone-20260922.iam.gserviceaccount.com"
}

import {
  to = google_secret_manager_secret_iam_member.runtime_secrets["openrouter_api_key"]
  id = "projects/metroai-vm-milestone-20260922/secrets/metroai-openrouter-api-key roles/secretmanager.secretAccessor serviceAccount:metroai-runtime@metroai-vm-milestone-20260922.iam.gserviceaccount.com"
}

import {
  to = google_secret_manager_secret_iam_member.runtime_secrets["transit_data_api_key"]
  id = "projects/metroai-vm-milestone-20260922/secrets/metroai-transit-data-api-key roles/secretmanager.secretAccessor serviceAccount:metroai-runtime@metroai-vm-milestone-20260922.iam.gserviceaccount.com"
}
