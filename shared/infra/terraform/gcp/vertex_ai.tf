# =============================================================================
# Quantum Portal — Vertex AI Resources
# Vector Search for fraud embeddings + training datasets
# =============================================================================

# ---------------------------------------------------------------------------
# Vector Search Index — fraud embeddings (768 dims, text-embedding-004 output)
# Used by RAG pipeline to retrieve similar fraud cases and quantum results
# ---------------------------------------------------------------------------
resource "google_vertex_ai_index" "fraud_embeddings" {
  display_name = "quantum-fraud-embeddings-${var.env}"
  description  = "Dense vector index for finance fraud cases and quantum circuit results. Powered by text-embedding-004 (768-dim). Used by RAG pipeline for fraud explanation and circuit similarity retrieval."
  region       = var.region

  metadata {
    contents_delta_uri = "gs://${google_storage_bucket.datasets.name}/vector-search/fraud-embeddings/"
    config {
      dimensions                  = 768
      approximate_neighbors_count = 150
      distance_measure_type       = "DOT_PRODUCT_DISTANCE"

      algorithm_config {
        tree_ah_config {
          leaf_node_embedding_count    = 1000
          leaf_nodes_to_search_percent = 10
        }
      }
    }
  }

  index_update_method = "STREAM_UPDATE" # real-time updates as new fraud data arrives

  labels = {
    env       = var.env
    purpose   = "fraud-rag"
    data_type = "financial"
  }
}

# ---------------------------------------------------------------------------
# Vector Search Index Endpoint — serves the fraud embeddings index
# ---------------------------------------------------------------------------
resource "google_vertex_ai_index_endpoint" "search_endpoint" {
  display_name = "quantum-search-endpoint-${var.env}"
  description  = "Deployed endpoint for fraud embedding vector search. Private endpoint within VPC; accessed by quantum-api service account."
  region       = var.region

  # Private endpoint — only accessible within VPC
  private_service_connect_config {
    enable_private_service_connect = true
    project_allowlist              = [var.project_id]
  }

  labels = {
    env     = var.env
    purpose = "fraud-rag"
  }
}

# ---------------------------------------------------------------------------
# Vertex AI Dataset — quantum circuit training data
# Used for: VQC hyperparameter search, noise mitigation model training
# ---------------------------------------------------------------------------
resource "google_vertex_ai_dataset" "quantum_training_data" {
  display_name        = "quantum-training-data-${var.env}"
  metadata_schema_uri = "gs://google-cloud-aiplatform/schema/dataset/metadata/tabular_1.0.0.yaml"
  region              = var.region

  labels = {
    env         = var.env
    data_domain = "quantum-circuits"
  }

  # Training data sourced from GCS after benchmark runs
  # Import: gcloud ai datasets import --dataset=DATASET_ID \
  #   --import-schema-uri=gs://google-cloud-aiplatform/schema/dataset/ioformat/tabular_1.0.0.yaml \
  #   --gcs-source=gs://PROJECT-quantum-datasets-prod/training/
}

# ---------------------------------------------------------------------------
# Vertex AI Endpoint — custom model serving (VQC fraud classifier)
# Separate from Vector Search; serves trained quantum ML models
# ---------------------------------------------------------------------------
resource "google_vertex_ai_endpoint" "vqc_fraud_endpoint" {
  name         = "vqc-fraud-endpoint-${var.env}"
  display_name = "VQC Fraud Classifier Endpoint"
  description  = "Serves the trained VQC-based fraud classification model. Supports traffic splitting for A/B testing classical vs quantum."
  location     = var.region
  network      = "projects/${var.project_id}/global/networks/${google_compute_network.quantum_vpc.name}"

  labels = {
    env   = var.env
    model = "vqc-fraud"
  }
}

# ---------------------------------------------------------------------------
# Vertex AI Workbench (managed notebook) — exploratory quantum circuit dev
# Used by ML engineers; not exposed to production traffic
# ---------------------------------------------------------------------------
resource "google_workbench_instance" "quantum_notebook" {
  count    = var.env == "prod" ? 0 : 1 # only in dev/staging
  name     = "quantum-notebook-${var.env}"
  location = var.zone

  gce_setup {
    machine_type = "n1-standard-4"

    accelerator_configs {
      type       = "NVIDIA_TESLA_T4"
      core_count = 1
    }

    boot_disk {
      disk_size_gb = 200
      disk_type    = "PD_SSD"
    }

    data_disks {
      disk_size_gb = 500
      disk_type    = "PD_STANDARD"
    }

    service_accounts {
      email = google_service_account.mlops_sa.email
    }
  }

  labels = {
    env     = var.env
    purpose = "quantum-development"
  }
}

# ---------------------------------------------------------------------------
# Artifact Registry — container images (replaces deprecated GCR)
# ---------------------------------------------------------------------------
resource "google_artifact_registry_repository" "quantum_images" {
  location      = var.region
  repository_id = "quantum-images-${var.env}"
  description   = "Docker images for quantum portal, API, workers, and ML models"
  format        = "DOCKER"

  cleanup_policies {
    id     = "keep-last-10"
    action = "KEEP"
    most_recent_versions {
      keep_count = 10
    }
  }

  cleanup_policies {
    id     = "delete-old-untagged"
    action = "DELETE"
    condition {
      tag_state  = "UNTAGGED"
      older_than = "604800s" # 7 days
    }
  }

  labels = {
    env = var.env
  }
}

# Grant GKE nodes read access to the Artifact Registry
resource "google_artifact_registry_repository_iam_member" "gke_reader" {
  location   = google_artifact_registry_repository.quantum_images.location
  repository = google_artifact_registry_repository.quantum_images.name
  role       = "roles/artifactregistry.reader"
  member     = "serviceAccount:${google_service_account.gke_sa.email}"
}
