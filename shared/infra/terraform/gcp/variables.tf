variable "project_id" {
  description = "GCP project ID"
  type        = string
}

variable "region" {
  description = "GCP region for all resources"
  type        = string
  default     = "us-central1"
}

variable "zone" {
  description = "GCP zone (used for node pools)"
  type        = string
  default     = "us-central1-a"
}

variable "env" {
  description = "Environment label: prod | staging | dev"
  type        = string
  default     = "prod"

  validation {
    condition     = contains(["prod", "staging", "dev"], var.env)
    error_message = "env must be prod, staging, or dev."
  }
}

variable "db_password" {
  description = "PostgreSQL root password (injected from Secret Manager via CI)"
  type        = string
  sensitive   = true
}

variable "db_tier" {
  description = "Cloud SQL machine tier"
  type        = string
  default     = "db-custom-4-15360" # 4 vCPU / 15 GB, handles 100 concurrent users
}

variable "redis_tier" {
  description = "Redis service tier: BASIC or STANDARD_HA"
  type        = string
  default     = "STANDARD_HA"
}

variable "redis_memory_gb" {
  description = "Redis memory size in GB"
  type        = number
  default     = 4
}

variable "dataset_bucket_location" {
  description = "GCS bucket location for datasets (multi-region for HA)"
  type        = string
  default     = "US"
}

variable "portal_image" {
  description = "Cloud Run container image for Next.js portal"
  type        = string
  default     = "gcr.io/PROJECT_ID/quantum-portal:latest"
}

variable "api_image" {
  description = "Cloud Run container image for FastAPI backend"
  type        = string
  default     = "gcr.io/PROJECT_ID/quantum-api:latest"
}

variable "min_portal_instances" {
  description = "Cloud Run minimum instances for portal (avoids cold start)"
  type        = number
  default     = 1
}

variable "max_portal_instances" {
  description = "Cloud Run maximum instances for portal"
  type        = number
  default     = 10
}

variable "max_api_instances" {
  description = "Cloud Run maximum instances for API"
  type        = number
  default     = 20
}

variable "alert_email" {
  description = "Email address for billing and ops alerts"
  type        = string
  default     = "temp.genai18@gmail.com"
}

variable "vpc_cidr" {
  description = "Primary CIDR range for quantum VPC"
  type        = string
  default     = "10.10.0.0/16"
}

variable "gke_pods_cidr" {
  description = "Secondary CIDR range for GKE pod IPs"
  type        = string
  default     = "10.20.0.0/14"
}

variable "gke_services_cidr" {
  description = "Secondary CIDR range for GKE service IPs"
  type        = string
  default     = "10.24.0.0/20"
}
