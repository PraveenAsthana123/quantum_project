output "gke_cluster_name" {
  description = "GKE cluster name"
  value       = google_container_cluster.quantum_portal.name
}

output "gke_cluster_endpoint" {
  description = "GKE cluster API server endpoint"
  value       = google_container_cluster.quantum_portal.endpoint
  sensitive   = true
}

output "portal_url" {
  description = "Cloud Run portal URL"
  value       = google_cloud_run_v2_service.portal.uri
}

output "api_url" {
  description = "Cloud Run API URL"
  value       = google_cloud_run_v2_service.api.uri
}

output "db_connection_name" {
  description = "Cloud SQL connection name (for Cloud SQL Auth Proxy)"
  value       = google_sql_database_instance.results_db.connection_name
}

output "db_private_ip" {
  description = "Cloud SQL private IP address"
  value       = google_sql_database_instance.results_db.private_ip_address
  sensitive   = true
}

output "redis_host" {
  description = "Redis (Memorystore) private IP"
  value       = google_redis_instance.job_queue.host
  sensitive   = true
}

output "datasets_bucket" {
  description = "GCS datasets bucket name"
  value       = google_storage_bucket.datasets.name
}

output "artifact_registry_url" {
  description = "Artifact Registry URL for pushing/pulling images"
  value       = "${var.region}-docker.pkg.dev/${var.project_id}/${google_artifact_registry_repository.quantum_images.repository_id}"
}

output "kms_keyring_id" {
  description = "KMS key ring resource ID"
  value       = google_kms_key_ring.quantum_keyring.id
}

output "fraud_vector_index_id" {
  description = "Vertex AI Vector Search index resource name"
  value       = google_vertex_ai_index.fraud_embeddings.id
}

output "search_endpoint_id" {
  description = "Vertex AI Vector Search endpoint resource name"
  value       = google_vertex_ai_index_endpoint.search_endpoint.id
}

output "vpc_id" {
  description = "VPC network self-link"
  value       = google_compute_network.quantum_vpc.self_link
}

output "vpc_name" {
  description = "VPC network name"
  value       = google_compute_network.quantum_vpc.name
}

output "portal_sa_email" {
  description = "Portal service account email"
  value       = google_service_account.portal_sa.email
}

output "api_sa_email" {
  description = "API service account email"
  value       = google_service_account.api_sa.email
}

output "mlops_sa_email" {
  description = "MLOps pipeline service account email"
  value       = google_service_account.mlops_sa.email
}
