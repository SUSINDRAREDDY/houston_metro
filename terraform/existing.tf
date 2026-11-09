# Please review these resources and move them into your main configuration files.

resource "google_secret_manager_secret" "metro_api_key" {
  annotations         = {}
  deletion_policy     = "DELETE"
  deletion_protection = false
  labels              = {}
  project             = "metroai-vm-milestone-20260922"
  secret_id           = "metroai-metro-api-key"
  version_aliases     = {}
  replication {
    auto {
    }
  }
}

resource "google_secret_manager_secret" "transit_data_api_key" {
  annotations         = {}
  deletion_policy     = "DELETE"
  deletion_protection = false
  labels              = {}
  project             = "metroai-vm-milestone-20260922"
  secret_id           = "metroai-transit-data-api-key"
  version_aliases     = {}
  replication {
    auto {
    }
  }
}

resource "google_compute_global_address" "database" {
  address         = "10.164.0.0"
  address_type    = "INTERNAL"
  deletion_policy = "DELETE"
  labels          = {}
  name            = "metroai-db-private-range"
  network         = "https://www.googleapis.com/compute/v1/projects/metroai-vm-milestone-20260922/global/networks/metroai-vpc"
  prefix_length   = 16
  project         = "metroai-vm-milestone-20260922"
  purpose         = "VPC_PEERING"
}

resource "google_artifact_registry_repository" "metroai" {
  cleanup_policy_dry_run = false
  deletion_policy        = "DELETE"
  description            = "MetroAI Milestone 3 images"
  format                 = "DOCKER"
  labels                 = {}
  location               = "us-central1"
  mode                   = "STANDARD_REPOSITORY"
  project                = "metroai-vm-milestone-20260922"
  repository_id          = "metroai"
  vulnerability_scanning_config {
    enablement_config = "DISABLED"
  }
}

resource "google_secret_manager_secret" "db_password" {
  annotations         = {}
  deletion_policy     = "DELETE"
  deletion_protection = false
  labels              = {}
  project             = "metroai-vm-milestone-20260922"
  secret_id           = "metroai-db-password"
  version_aliases     = {}
  replication {
    auto {
    }
  }
}

resource "google_compute_subnetwork" "metroai" {
  lifecycle {
    prevent_destroy = true
  }

  allow_subnet_cidr_routes_overlap = false
  deletion_policy                  = "DELETE"
  ip_cidr_range                    = "10.42.0.0/24"
  name                             = "metroai-subnet"
  network                          = "https://www.googleapis.com/compute/v1/projects/metroai-vm-milestone-20260922/global/networks/metroai-vpc"
  private_ip_google_access         = true
  private_ipv6_google_access       = "DISABLE_GOOGLE_ACCESS"
  project                          = "metroai-vm-milestone-20260922"
  purpose                          = "PRIVATE"
  region                           = "us-central1"
  stack_type                       = "IPV4_ONLY"
  secondary_ip_range {
    ip_cidr_range           = "10.153.0.0/17"
    range_name              = "gke-metroai-gke-pods-08bff698"
    reserved_internal_range = "networkconnectivity.googleapis.com/projects/metroai-vm-milestone-20260922/locations/global/internalRanges/gke-metroai-gke-pods-08bff698"
  }
}

resource "google_compute_network" "metroai" {
  lifecycle {
    prevent_destroy = true
  }

  auto_create_subnetworks                   = false
  bgp_always_compare_med                    = false
  bgp_best_path_selection_mode              = "LEGACY"
  delete_bgp_always_compare_med             = false
  delete_default_routes_on_create           = false
  deletion_policy                           = "DELETE"
  enable_ula_internal_ipv6                  = false
  mtu                                       = 0
  name                                      = "metroai-vpc"
  network_firewall_policy_enforcement_order = "AFTER_CLASSIC_FIREWALL"
  project                                   = "metroai-vm-milestone-20260922"
  routing_mode                              = "REGIONAL"
}

resource "google_secret_manager_secret" "db_admin_password" {
  annotations         = {}
  deletion_policy     = "DELETE"
  deletion_protection = false
  labels              = {}
  project             = "metroai-vm-milestone-20260922"
  secret_id           = "metroai-db-admin-password"
  version_aliases     = {}
  replication {
    auto {
    }
  }
}

resource "google_secret_manager_secret" "openrouter_api_key" {
  annotations         = {}
  deletion_policy     = "DELETE"
  deletion_protection = false
  labels              = {}
  project             = "metroai-vm-milestone-20260922"
  secret_id           = "metroai-openrouter-api-key"
  version_aliases     = {}
  replication {
    auto {
    }
  }
}

resource "google_service_account" "runtime" {
  account_id      = "metroai-runtime"
  deletion_policy = "DELETE"
  disabled        = false
  display_name    = "MetroAI Milestone 4 runtime"
  project         = "metroai-vm-milestone-20260922"
}

resource "google_sql_database_instance" "metroai" {
  lifecycle {
    prevent_destroy = true
  }

  database_version                     = "POSTGRES_16"
  deletion_policy                      = "DELETE"
  deletion_protection                  = true
  enforce_new_sql_network_architecture = true
  instance_type                        = "CLOUD_SQL_INSTANCE"
  maintenance_version                  = "POSTGRES_16_15.R20260712.01_33"
  name                                 = "metroai-postgres"
  node_count                           = 0
  project                              = "metroai-vm-milestone-20260922"
  region                               = "us-central1"
  replica_names                        = []
  replication_cluster {
  }
  settings {
    activation_policy                = "ALWAYS"
    auto_upgrade_enabled             = false
    availability_type                = "ZONAL"
    connector_enforcement            = "NOT_REQUIRED"
    data_disk_provisioned_iops       = 0
    data_disk_provisioned_throughput = 0
    deletion_protection_enabled      = true
    disk_autoresize                  = false
    disk_autoresize_limit            = 0
    disk_size                        = 10
    disk_type                        = "PD_SSD"
    edition                          = "ENTERPRISE"
    enable_dataplex_integration      = true
    enable_google_ml_integration     = false
    pricing_plan                     = "PER_USE"
    replication_lag_max_seconds      = 31536000
    retain_backups_on_delete         = false
    tier                             = "db-f1-micro"
    user_labels                      = {}
    backup_configuration {
      binary_log_enabled             = false
      enabled                        = true
      point_in_time_recovery_enabled = false
      start_time                     = "08:00"
      transaction_log_retention_days = 7
      backup_retention_settings {
        retained_backups = 7
        retention_unit   = "COUNT"
      }
    }
    data_cache_config {
      data_cache_enabled = false
    }
    ip_configuration {
      custom_subject_alternative_names              = []
      enable_private_path_for_google_cloud_services = false
      ipv4_enabled                                  = false
      private_network                               = "projects/metroai-vm-milestone-20260922/global/networks/metroai-vpc"
      server_ca_mode                                = "GOOGLE_MANAGED_INTERNAL_CA"
      ssl_mode                                      = "ENCRYPTED_ONLY"
    }
    location_preference {
      zone = "us-central1-f"
    }
  }
}

resource "google_compute_global_address" "web" {
  address         = "136.81.119.160"
  address_type    = "EXTERNAL"
  deletion_policy = "DELETE"
  ip_version      = "IPV4"
  labels          = {}
  name            = "metroai-gke-ip"
  prefix_length   = 0
  project         = "metroai-vm-milestone-20260922"
}

resource "google_sql_database" "metroai" {
  charset         = "UTF8"
  collation       = "en_US.UTF8"
  deletion_policy = "DELETE"
  instance        = "metroai-postgres"
  name            = "metroai"
  project         = "metroai-vm-milestone-20260922"
}

resource "google_service_networking_connection" "database" {
  deletion_policy         = "DELETE"
  network                 = "projects/metroai-vm-milestone-20260922/global/networks/metroai-vpc"
  reserved_peering_ranges = ["metroai-db-private-range"]
  service                 = "servicenetworking.googleapis.com"
}

resource "google_storage_bucket" "uploads" {
  lifecycle {
    prevent_destroy = true
  }

  default_event_based_hold    = false
  deletion_policy             = "DELETE"
  enable_object_retention     = false
  force_destroy               = false
  labels                      = {}
  location                    = "US-CENTRAL1"
  name                        = "metroai-vm-milestone-20260922-uploads"
  project                     = "metroai-vm-milestone-20260922"
  public_access_prevention    = "enforced"
  requester_pays              = false
  storage_class               = "STANDARD"
  uniform_bucket_level_access = true
  hierarchical_namespace {
    enabled = false
  }
  soft_delete_policy {
    retention_duration_seconds = 604800
  }
}

resource "google_container_cluster" "metroai" {
  lifecycle {
    prevent_destroy = true
    # The provider proposes gke://* when the live Autopilot API returns an empty list.
    ignore_changes = [autopilot_privileged_admission]
  }

  datapath_provider                        = "ADVANCED_DATAPATH"
  deletion_policy                          = "DELETE"
  deletion_protection                      = true
  disable_l4_lb_firewall_reconciliation    = false
  enable_autopilot                         = true
  enable_cilium_clusterwide_network_policy = false
  enable_fqdn_network_policy               = false
  enable_kubernetes_alpha                  = false
  enable_l4_ilb_subsetting                 = false
  enable_legacy_abac                       = false
  enable_multi_networking                  = false
  enable_tpu                               = false
  location                                 = "us-central1"
  logging_service                          = "logging.googleapis.com/kubernetes"
  monitoring_service                       = "monitoring.googleapis.com/kubernetes"
  name                                     = "metroai-gke"
  network                                  = "projects/metroai-vm-milestone-20260922/global/networks/metroai-vpc"
  networking_mode                          = "VPC_NATIVE"
  node_locations                           = ["us-central1-a", "us-central1-b", "us-central1-c", "us-central1-f"]
  project                                  = "metroai-vm-milestone-20260922"
  resource_labels                          = {}
  subnetwork                               = "projects/metroai-vm-milestone-20260922/regions/us-central1/subnetworks/metroai-subnet"
  addons_config {
    gce_persistent_disk_csi_driver_config {
      enabled = true
    }
    gcp_filestore_csi_driver_config {
      enabled = true
    }
    gcs_fuse_csi_driver_config {
      enabled = true
    }
    node_readiness_config {
      enabled = false
    }
    parallelstore_csi_driver_config {
      enabled = true
    }
  }
  anonymous_authentication_config {
    mode = "LIMITED"
  }
  control_plane_endpoints_config {
    dns_endpoint_config {
      allow_external_traffic    = false
      enable_k8s_certs_via_dns  = false
      enable_k8s_tokens_via_dns = false
      endpoint                  = "gke-08bff69806b746d9851b63c67d90efd7580c-1065898950357.us-central1.gke.goog"
    }
    ip_endpoints_config {
      enabled = true
    }
  }
  database_encryption {
    state = "DECRYPTED"
  }
  dns_config {
    cluster_dns        = "CLOUD_DNS"
    cluster_dns_domain = "cluster.local"
    cluster_dns_scope  = "CLUSTER_SCOPE"
  }
  gateway_api_config {
    channel = "CHANNEL_STANDARD"
  }
  ip_allocation_policy {
    cluster_secondary_range_name = "gke-metroai-gke-pods-08bff698"
    stack_type                   = "IPV4"
    network_tier_config {
      network_tier = "NETWORK_TIER_DEFAULT"
    }
    pod_cidr_overprovision_config {
      disabled = false
    }
  }
  logging_config {
    enable_components = ["SYSTEM_COMPONENTS", "WORKLOADS"]
  }
  master_auth {
    client_certificate_config {
      issue_client_certificate = false
    }
  }
  monitoring_config {
    enable_components = ["SYSTEM_COMPONENTS", "STORAGE", "HPA", "POD", "DAEMONSET", "DEPLOYMENT", "STATEFULSET", "CADVISOR", "KUBELET", "DCGM", "JOBSET"]
    advanced_datapath_observability_config {
      enable_metrics = true
      enable_relay   = false
    }
    managed_prometheus {
      enabled = true
    }
  }
  node_creation_config {
    node_creation_mode = "VIA_KUBELET"
  }
  node_pool_auto_config {
    resource_manager_tags = {}
    node_kubelet_config {
      insecure_kubelet_readonly_port_enabled = "FALSE"
    }
  }
  node_pool_defaults {
    node_config_defaults {
      insecure_kubelet_readonly_port_enabled = "FALSE"
      logging_variant                        = "DEFAULT"
      gcfs_config {
        enabled = true
      }
    }
  }
  notification_config {
    pubsub {
      enabled = false
    }
  }
  pod_autoscaling {
    hpa_profile = "PERFORMANCE"
  }
  private_cluster_config {
    enable_private_endpoint = false
    enable_private_nodes    = false
    master_global_access_config {
      enabled = false
    }
  }
  rbac_binding_config {
    enable_insecure_binding_system_authenticated   = false
    enable_insecure_binding_system_unauthenticated = false
  }
  release_channel {
    channel = "REGULAR"
  }
  secret_manager_config {
    enabled = false
  }
  secret_sync_config {
    enabled = false
  }
  security_posture_config {
    mode               = "BASIC"
    vulnerability_mode = "VULNERABILITY_MODE_UNSPECIFIED"
  }
  service_external_ips_config {
    enabled = false
  }
  vertical_pod_autoscaling {
    enabled = true
  }
  workload_identity_config {
    workload_pool = "metroai-vm-milestone-20260922.svc.id.goog"
  }
}
