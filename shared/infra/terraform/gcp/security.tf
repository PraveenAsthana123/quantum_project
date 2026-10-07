# =============================================================================
# Quantum Portal — GCP Security: KMS, Secrets, VPC, Firewall
# =============================================================================

# ---------------------------------------------------------------------------
# KMS Key Ring + Crypto Keys (CMEK)
# ---------------------------------------------------------------------------
resource "google_kms_key_ring" "quantum_keyring" {
  name     = "quantum-keyring-${var.env}"
  location = var.region
}

resource "google_kms_crypto_key" "dataset_key" {
  name            = "quantum-dataset-key"
  key_ring        = google_kms_key_ring.quantum_keyring.id
  rotation_period = "7776000s" # 90-day automatic rotation

  lifecycle {
    prevent_destroy = true
  }

  labels = {
    purpose = "dataset-encryption"
    env     = var.env
  }
}

resource "google_kms_crypto_key" "bq_key" {
  name            = "quantum-bq-key"
  key_ring        = google_kms_key_ring.quantum_keyring.id
  rotation_period = "7776000s"

  lifecycle {
    prevent_destroy = true
  }

  labels = {
    purpose = "bigquery-encryption"
    env     = var.env
  }
}

resource "google_kms_crypto_key" "db_key" {
  name            = "quantum-db-key"
  key_ring        = google_kms_key_ring.quantum_keyring.id
  rotation_period = "7776000s"

  lifecycle {
    prevent_destroy = true
  }

  labels = {
    purpose = "database-encryption"
    env     = var.env
  }
}

# Grant GCS service account permission to use the dataset CMEK key
data "google_storage_project_service_account" "gcs_sa" {}

resource "google_kms_crypto_key_iam_member" "storage_sa_encrypter" {
  crypto_key_id = google_kms_crypto_key.dataset_key.id
  role          = "roles/cloudkms.cryptoKeyEncrypterDecrypter"
  member        = "serviceAccount:${data.google_storage_project_service_account.gcs_sa.email_address}"
}

# Grant BigQuery service account permission to use the BQ CMEK key
data "google_bigquery_default_service_account" "bq_sa" {}

resource "google_kms_crypto_key_iam_member" "bq_sa_encrypter" {
  crypto_key_id = google_kms_crypto_key.bq_key.id
  role          = "roles/cloudkms.cryptoKeyEncrypterDecrypter"
  member        = "serviceAccount:${data.google_bigquery_default_service_account.bq_sa.email}"
}

# ---------------------------------------------------------------------------
# Secret Manager — credentials + API keys
# ---------------------------------------------------------------------------
resource "google_secret_manager_secret" "db_password" {
  secret_id = "quantum-db-password-${var.env}"

  replication {
    auto {}
  }

  labels = {
    env     = var.env
    purpose = "database"
  }
}

resource "google_secret_manager_secret_version" "db_password_v1" {
  secret      = google_secret_manager_secret.db_password.id
  secret_data = var.db_password
}

resource "google_secret_manager_secret" "qpu_api_key" {
  secret_id = "quantum-qpu-api-key-${var.env}"

  replication {
    auto {}
  }

  labels = {
    env     = var.env
    purpose = "qpu-access"
  }
}

# Placeholder version — update via gcloud or CI pipeline with real QPU key
resource "google_secret_manager_secret_version" "qpu_api_key_placeholder" {
  secret      = google_secret_manager_secret.qpu_api_key.id
  secret_data = "REPLACE_WITH_REAL_QPU_API_KEY"
}

resource "google_secret_manager_secret" "nextauth_secret" {
  secret_id = "quantum-nextauth-secret-${var.env}"

  replication {
    auto {}
  }
}

resource "google_secret_manager_secret_version" "nextauth_secret_v1" {
  secret      = google_secret_manager_secret.nextauth_secret.id
  secret_data = "REPLACE_WITH_GENERATED_NEXTAUTH_SECRET_32_CHARS"
}

resource "google_secret_manager_secret" "mlflow_db_password" {
  secret_id = "quantum-mlflow-db-password-${var.env}"

  replication {
    auto {}
  }
}

resource "google_secret_manager_secret_version" "mlflow_db_password_v1" {
  secret      = google_secret_manager_secret.mlflow_db_password.id
  secret_data = "REPLACE_WITH_MLFLOW_DB_PASSWORD"
}

# ---------------------------------------------------------------------------
# VPC + Subnets
# ---------------------------------------------------------------------------
resource "google_compute_network" "quantum_vpc" {
  name                    = "quantum-vpc-${var.env}"
  auto_create_subnetworks = false
  routing_mode            = "REGIONAL"
  mtu                     = 1500
}

resource "google_compute_subnetwork" "gke_subnet" {
  name          = "quantum-gke-subnet-${var.env}"
  ip_cidr_range = var.vpc_cidr
  region        = var.region
  network       = google_compute_network.quantum_vpc.id

  private_ip_google_access = true # allows nodes to reach Google APIs without NAT

  secondary_ip_range {
    range_name    = "pods"
    ip_cidr_range = var.gke_pods_cidr
  }

  secondary_ip_range {
    range_name    = "services"
    ip_cidr_range = var.gke_services_cidr
  }

  log_config {
    aggregation_interval = "INTERVAL_5_SEC"
    flow_sampling        = 0.5
    metadata             = "INCLUDE_ALL_METADATA"
  }
}

# Cloud NAT — lets private GKE nodes reach the internet for image pulls
resource "google_compute_router" "quantum_router" {
  name    = "quantum-router-${var.env}"
  region  = var.region
  network = google_compute_network.quantum_vpc.id
}

resource "google_compute_router_nat" "quantum_nat" {
  name                               = "quantum-nat-${var.env}"
  router                             = google_compute_router.quantum_router.name
  region                             = var.region
  nat_ip_allocate_option             = "AUTO_ONLY"
  source_subnetwork_ip_ranges_to_nat = "ALL_SUBNETWORKS_ALL_IP_RANGES"

  log_config {
    enable = true
    filter = "ERRORS_ONLY"
  }
}

# ---------------------------------------------------------------------------
# Firewall rules
# ---------------------------------------------------------------------------

# Deny all ingress by default (GCP default-deny is implicit, but explicit is clearer)
resource "google_compute_firewall" "deny_all_ingress" {
  name    = "quantum-deny-all-ingress-${var.env}"
  network = google_compute_network.quantum_vpc.name

  priority  = 65534
  direction = "INGRESS"

  deny {
    protocol = "all"
  }

  source_ranges = ["0.0.0.0/0"]

  log_config {
    metadata = "INCLUDE_ALL_METADATA"
  }
}

# Allow internal VPC traffic (GKE node-to-node, services, health checks)
resource "google_compute_firewall" "allow_internal" {
  name    = "quantum-allow-internal-${var.env}"
  network = google_compute_network.quantum_vpc.name

  priority  = 1000
  direction = "INGRESS"

  allow {
    protocol = "tcp"
  }
  allow {
    protocol = "udp"
  }
  allow {
    protocol = "icmp"
  }

  source_ranges = [var.vpc_cidr, var.gke_pods_cidr, var.gke_services_cidr]
}

# Allow GCP health checks (load balancer probes)
resource "google_compute_firewall" "allow_health_checks" {
  name    = "quantum-allow-health-checks-${var.env}"
  network = google_compute_network.quantum_vpc.name

  priority  = 1000
  direction = "INGRESS"

  allow {
    protocol = "tcp"
    ports    = ["8080", "8000", "3001"]
  }

  # GCP load balancer health check IP ranges
  source_ranges = ["130.211.0.0/22", "35.191.0.0/16"]
}

# Allow SSH only from IAP (Identity-Aware Proxy) for debugging
resource "google_compute_firewall" "allow_iap_ssh" {
  name    = "quantum-allow-iap-ssh-${var.env}"
  network = google_compute_network.quantum_vpc.name

  priority  = 1000
  direction = "INGRESS"

  allow {
    protocol = "tcp"
    ports    = ["22"]
  }

  source_ranges = ["35.235.240.0/20"] # IAP TCP forwarding range
}

# ---------------------------------------------------------------------------
# VPC Service Controls — perimeter protecting BigQuery + Storage
# Access Context Manager requires org-level permissions; commented out by
# default to avoid errors on projects without org policy binding.
# Uncomment and set var.access_policy_id to enable.
# ---------------------------------------------------------------------------

# resource "google_access_context_manager_service_perimeter" "quantum_perimeter" {
#   parent = "accessPolicies/${var.access_policy_id}"
#   name   = "accessPolicies/${var.access_policy_id}/servicePerimeters/quantum_perimeter_${var.env}"
#   title  = "Quantum Portal Data Perimeter (${var.env})"
#
#   status {
#     restricted_services = [
#       "bigquery.googleapis.com",
#       "storage.googleapis.com",
#     ]
#
#     resources = [
#       "projects/${var.project_id}",
#     ]
#
#     access_levels = [
#       google_access_context_manager_access_level.quantum_internal.name,
#     ]
#
#     vpc_accessible_services {
#       enable_restriction = true
#       allowed_services   = ["bigquery.googleapis.com", "storage.googleapis.com"]
#     }
#   }
# }
