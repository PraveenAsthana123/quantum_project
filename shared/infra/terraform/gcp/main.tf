# =============================================================================
# Quantum Portal — GCP Core Infrastructure
# Target: 100 concurrent users, 100 GB finance/fraud dataset
# =============================================================================

# ---------------------------------------------------------------------------
# GKE Autopilot cluster
# Autopilot handles node provisioning; workloads are pod-level billed.
# ---------------------------------------------------------------------------
resource "google_container_cluster" "quantum_portal" {
  provider = google-beta
  name     = "quantum-portal-${var.env}"
  location = var.region

  enable_autopilot = true

  network    = google_compute_network.quantum_vpc.id
  subnetwork = google_compute_subnetwork.gke_subnet.id

  release_channel {
    channel = "REGULAR"
  }

  ip_allocation_policy {
    cluster_secondary_range_name  = "pods"
    services_secondary_range_name = "services"
  }

  private_cluster_config {
    enable_private_nodes    = true
    enable_private_endpoint = false
    master_ipv4_cidr_block  = "172.16.0.0/28"
  }

  master_authorized_networks_config {
    cidr_blocks {
      cidr_block   = "0.0.0.0/0"
      display_name = "public-api-server" # narrow this per org policy
    }
  }

  addons_config {
    http_load_balancing {
      disabled = false
    }
    horizontal_pod_autoscaling {
      disabled = false
    }
    gce_persistent_disk_csi_driver_config {
      enabled = true
    }
  }

  workload_identity_config {
    workload_pool = "${var.project_id}.svc.id.goog"
  }

  logging_config {
    enable_components = ["SYSTEM_COMPONENTS", "WORKLOADS"]
  }

  monitoring_config {
    enable_components = ["SYSTEM_COMPONENTS", "WORKLOADS"]
    managed_prometheus {
      enabled = true
    }
  }

  labels = {
    env     = var.env
    project = "quantum-portal"
  }
}

# ---------------------------------------------------------------------------
# Cloud Run — Next.js portal (frontend)
# ---------------------------------------------------------------------------
resource "google_cloud_run_v2_service" "portal" {
  name     = "quantum-portal-${var.env}"
  location = var.region
  ingress  = "INGRESS_TRAFFIC_ALL"

  template {
    scaling {
      min_instance_count = var.min_portal_instances
      max_instance_count = var.max_portal_instances
    }

    vpc_access {
      connector = google_vpc_access_connector.serverless_connector.id
      egress    = "PRIVATE_RANGES_ONLY"
    }

    containers {
      image = var.portal_image

      ports {
        container_port = 3001
      }

      resources {
        limits = {
          cpu    = "2"
          memory = "2Gi"
        }
        cpu_idle = true
        startup_cpu_boost = true
      }

      env {
        name  = "NODE_ENV"
        value = "production"
      }
      env {
        name  = "API_BASE_URL"
        value = "https://${google_cloud_run_v2_service.api.uri}"
      }
      env {
        name = "NEXTAUTH_SECRET"
        value_source {
          secret_key_ref {
            secret  = google_secret_manager_secret.nextauth_secret.secret_id
            version = "latest"
          }
        }
      }
    }

    service_account = google_service_account.portal_sa.email
  }

  labels = {
    env     = var.env
    component = "portal"
  }

  depends_on = [google_secret_manager_secret_version.nextauth_secret_v1]
}

# Allow unauthenticated access to Cloud Run portal (public web app)
resource "google_cloud_run_v2_service_iam_member" "portal_public" {
  project  = var.project_id
  location = var.region
  name     = google_cloud_run_v2_service.portal.name
  role     = "roles/run.invoker"
  member   = "allUsers"
}

# ---------------------------------------------------------------------------
# Cloud Run — FastAPI backend (API)
# ---------------------------------------------------------------------------
resource "google_cloud_run_v2_service" "api" {
  name     = "quantum-api-${var.env}"
  location = var.region
  ingress  = "INGRESS_TRAFFIC_ALL"

  template {
    scaling {
      min_instance_count = 1
      max_instance_count = var.max_api_instances
    }

    vpc_access {
      connector = google_vpc_access_connector.serverless_connector.id
      egress    = "PRIVATE_RANGES_ONLY"
    }

    containers {
      image = var.api_image

      ports {
        container_port = 8000
      }

      resources {
        limits = {
          cpu    = "4"
          memory = "4Gi"
        }
        cpu_idle = false # keep warm for low-latency API responses
      }

      env {
        name  = "ENV"
        value = var.env
      }
      env {
        name  = "REDIS_HOST"
        value = google_redis_instance.job_queue.host
      }
      env {
        name  = "REDIS_PORT"
        value = tostring(google_redis_instance.job_queue.port)
      }
      env {
        name  = "DB_HOST"
        value = google_sql_database_instance.results_db.private_ip_address
      }
      env {
        name  = "DB_NAME"
        value = "quantum_results"
      }
      env {
        name = "DB_PASSWORD"
        value_source {
          secret_key_ref {
            secret  = google_secret_manager_secret.db_password.secret_id
            version = "latest"
          }
        }
      }
      env {
        name = "QPU_API_KEY"
        value_source {
          secret_key_ref {
            secret  = google_secret_manager_secret.qpu_api_key.secret_id
            version = "latest"
          }
        }
      }
    }

    service_account = google_service_account.api_sa.email
  }

  depends_on = [
    google_secret_manager_secret_version.db_password_v1,
    google_secret_manager_secret_version.qpu_api_key_placeholder,
  ]
}

# ---------------------------------------------------------------------------
# Cloud SQL — PostgreSQL 16 for circuit results + experiment metadata
# ---------------------------------------------------------------------------
resource "google_sql_database_instance" "results_db" {
  name             = "quantum-results-${var.env}"
  database_version = "POSTGRES_16"
  region           = var.region

  deletion_protection = var.env == "prod" ? true : false

  settings {
    tier              = var.db_tier
    availability_type = var.env == "prod" ? "REGIONAL" : "ZONAL"
    disk_autoresize   = true
    disk_size         = 100 # GB, grows automatically up to disk_autoresize_limit
    disk_autoresize_limit = 500

    backup_configuration {
      enabled                        = true
      point_in_time_recovery_enabled = true
      start_time                     = "02:00"
      transaction_log_retention_days = 7
      backup_retention_settings {
        retained_backups = 30
      }
    }

    ip_configuration {
      ipv4_enabled    = false
      private_network = google_compute_network.quantum_vpc.id
      require_ssl     = true
    }

    database_flags {
      name  = "max_connections"
      value = "200" # headroom above 100 concurrent users
    }
    database_flags {
      name  = "log_min_duration_statement"
      value = "1000" # log queries slower than 1s
    }

    insights_config {
      query_insights_enabled  = true
      query_string_length     = 4096
      record_application_tags = true
      record_client_address   = false
    }

    maintenance_window {
      day          = 7 # Sunday
      hour         = 3
      update_track = "stable"
    }
  }

  depends_on = [google_service_networking_connection.private_vpc_connection]
}

resource "google_sql_database" "quantum_results" {
  name     = "quantum_results"
  instance = google_sql_database_instance.results_db.name
}

resource "google_sql_user" "api_user" {
  name     = "quantum_api"
  instance = google_sql_database_instance.results_db.name
  password = var.db_password
}

# ---------------------------------------------------------------------------
# Redis (Memorystore) — job queue + circuit result cache
# ---------------------------------------------------------------------------
resource "google_redis_instance" "job_queue" {
  name           = "quantum-job-queue-${var.env}"
  tier           = var.redis_tier
  memory_size_gb = var.redis_memory_gb
  region         = var.region

  authorized_network = google_compute_network.quantum_vpc.id
  connect_mode       = "PRIVATE_SERVICE_ACCESS"

  redis_version     = "REDIS_7_0"
  display_name      = "Quantum Job Queue"

  redis_configs = {
    maxmemory-policy = "allkeys-lru"
    notify-keyspace-events = "Ex" # expiry events for job TTL tracking
  }

  labels = {
    env       = var.env
    component = "job-queue"
  }
}

# ---------------------------------------------------------------------------
# GCS — Dataset bucket (100 GB nearline, CMEK-encrypted)
# ---------------------------------------------------------------------------
resource "google_storage_bucket" "datasets" {
  name          = "${var.project_id}-quantum-datasets-${var.env}"
  location      = var.dataset_bucket_location
  storage_class = "NEARLINE"
  force_destroy = false

  uniform_bucket_level_access = true

  versioning {
    enabled = true
  }

  lifecycle_rule {
    action {
      type          = "SetStorageClass"
      storage_class = "COLDLINE"
    }
    condition {
      age = 90 # move to coldline after 90 days (raw datasets rarely re-read)
    }
  }

  lifecycle_rule {
    action {
      type = "Delete"
    }
    condition {
      num_newer_versions = 3 # keep only 3 versions per object
    }
  }

  encryption {
    default_kms_key_name = google_kms_crypto_key.dataset_key.id
  }

  labels = {
    env       = var.env
    data_type = "quantum-datasets"
  }

  depends_on = [google_kms_crypto_key_iam_member.storage_sa_encrypter]
}

# ---------------------------------------------------------------------------
# BigQuery — Analytics layer
# ---------------------------------------------------------------------------
resource "google_bigquery_dataset" "quantum_analytics" {
  dataset_id  = "quantum_analytics_${var.env}"
  location    = var.region
  description = "Quantum portal analytics: fraud transactions, circuit benchmarks, model metrics"

  default_encryption_configuration {
    kms_key_name = google_kms_crypto_key.bq_key.id
  }

  labels = {
    env = var.env
  }

  # Restrict access to service accounts only; no allUsers
  access {
    role          = "OWNER"
    special_group = "projectOwners"
  }
  access {
    role           = "WRITER"
    user_by_email  = google_service_account.api_sa.email
  }
  access {
    role           = "READER"
    user_by_email  = google_service_account.mlops_sa.email
  }

  delete_contents_on_destroy = var.env != "prod"
}

resource "google_bigquery_table" "fraud_transactions" {
  dataset_id = google_bigquery_dataset.quantum_analytics.dataset_id
  table_id   = "fraud_transactions"
  description = "Finance fraud transaction data with classical + quantum prediction labels"

  time_partitioning {
    type  = "DAY"
    field = "transaction_timestamp"
  }

  clustering = ["merchant_category", "fraud_label"]

  encryption_configuration {
    kms_key_name = google_kms_crypto_key.bq_key.id
  }

  schema = jsonencode([
    { name = "transaction_id",        type = "STRING",    mode = "REQUIRED" },
    { name = "transaction_timestamp", type = "TIMESTAMP", mode = "REQUIRED" },
    { name = "amount_usd",            type = "FLOAT64",   mode = "REQUIRED" },
    { name = "merchant_category",     type = "STRING",    mode = "NULLABLE" },
    { name = "cardholder_id",         type = "STRING",    mode = "REQUIRED" },
    { name = "classical_fraud_score", type = "FLOAT64",   mode = "NULLABLE" },
    { name = "quantum_fraud_score",   type = "FLOAT64",   mode = "NULLABLE" },
    { name = "fraud_label",           type = "BOOL",      mode = "NULLABLE" },
    { name = "model_version",         type = "STRING",    mode = "NULLABLE" },
    { name = "features_json",         type = "JSON",      mode = "NULLABLE" },
    { name = "circuit_depth",         type = "INT64",     mode = "NULLABLE" },
    { name = "backend",               type = "STRING",    mode = "NULLABLE" },
  ])
}

resource "google_bigquery_table" "quantum_benchmarks" {
  dataset_id = google_bigquery_dataset.quantum_analytics.dataset_id
  table_id   = "quantum_benchmarks"
  description = "Weekly benchmark results across all 30 quantum projects"

  time_partitioning {
    type  = "DAY"
    field = "run_timestamp"
  }

  clustering = ["project_id", "backend"]

  encryption_configuration {
    kms_key_name = google_kms_crypto_key.bq_key.id
  }

  schema = jsonencode([
    { name = "benchmark_id",       type = "STRING",    mode = "REQUIRED" },
    { name = "project_id",         type = "STRING",    mode = "REQUIRED" },
    { name = "run_timestamp",      type = "TIMESTAMP", mode = "REQUIRED" },
    { name = "backend",            type = "STRING",    mode = "REQUIRED" },
    { name = "circuit_depth",      type = "INT64",     mode = "NULLABLE" },
    { name = "num_qubits",         type = "INT64",     mode = "NULLABLE" },
    { name = "gate_count",         type = "INT64",     mode = "NULLABLE" },
    { name = "fidelity",           type = "FLOAT64",   mode = "NULLABLE" },
    { name = "execution_time_ms",  type = "FLOAT64",   mode = "NULLABLE" },
    { name = "classical_accuracy", type = "FLOAT64",   mode = "NULLABLE" },
    { name = "quantum_accuracy",   type = "FLOAT64",   mode = "NULLABLE" },
    { name = "noise_level",        type = "FLOAT64",   mode = "NULLABLE" },
    { name = "error_mitigation",   type = "STRING",    mode = "NULLABLE" },
    { name = "model_version",      type = "STRING",    mode = "NULLABLE" },
    { name = "cost_usd",           type = "FLOAT64",   mode = "NULLABLE" },
    { name = "metadata_json",      type = "JSON",      mode = "NULLABLE" },
  ])
}

# ---------------------------------------------------------------------------
# VPC Access Connector — lets Cloud Run reach VPC private IPs
# ---------------------------------------------------------------------------
resource "google_vpc_access_connector" "serverless_connector" {
  name          = "quantum-connector-${var.env}"
  region        = var.region
  network       = google_compute_network.quantum_vpc.name
  ip_cidr_range = "10.8.0.0/28"
  min_instances = 2
  max_instances = 10
}

# ---------------------------------------------------------------------------
# Service accounts
# ---------------------------------------------------------------------------
resource "google_service_account" "portal_sa" {
  account_id   = "quantum-portal-sa-${var.env}"
  display_name = "Quantum Portal Cloud Run SA"
}

resource "google_service_account" "api_sa" {
  account_id   = "quantum-api-sa-${var.env}"
  display_name = "Quantum API Cloud Run SA"
}

resource "google_service_account" "gke_sa" {
  account_id   = "quantum-gke-sa-${var.env}"
  display_name = "Quantum GKE Node SA"
}

resource "google_service_account" "mlops_sa" {
  account_id   = "quantum-mlops-sa-${var.env}"
  display_name = "Quantum MLOps Pipeline SA"
}

# API SA needs BQ write, GCS read, Secret Manager access
resource "google_project_iam_member" "api_bq_writer" {
  project = var.project_id
  role    = "roles/bigquery.dataEditor"
  member  = "serviceAccount:${google_service_account.api_sa.email}"
}

resource "google_project_iam_member" "api_gcs_reader" {
  project = var.project_id
  role    = "roles/storage.objectViewer"
  member  = "serviceAccount:${google_service_account.api_sa.email}"
}

resource "google_project_iam_member" "api_secret_accessor" {
  project = var.project_id
  role    = "roles/secretmanager.secretAccessor"
  member  = "serviceAccount:${google_service_account.api_sa.email}"
}

resource "google_project_iam_member" "mlops_vertex_user" {
  project = var.project_id
  role    = "roles/aiplatform.user"
  member  = "serviceAccount:${google_service_account.mlops_sa.email}"
}

# Private VPC connection for Cloud SQL
resource "google_compute_global_address" "private_ip_range" {
  name          = "quantum-private-ip-range"
  purpose       = "VPC_PEERING"
  address_type  = "INTERNAL"
  prefix_length = 16
  network       = google_compute_network.quantum_vpc.id
}

resource "google_service_networking_connection" "private_vpc_connection" {
  network                 = google_compute_network.quantum_vpc.id
  service                 = "servicenetworking.googleapis.com"
  reserved_peering_ranges = [google_compute_global_address.private_ip_range.name]
}
