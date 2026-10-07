# =============================================================================
# Quantum Portal — Azure Terraform Variables
# =============================================================================

variable "env" {
  description = "Deployment environment: prod | staging | dev"
  type        = string
  default     = "prod"

  validation {
    condition     = contains(["prod", "staging", "dev"], var.env)
    error_message = "env must be prod, staging, or dev."
  }
}

variable "location" {
  description = "Primary Azure region"
  type        = string
  default     = "eastus"
}

variable "project_name" {
  description = "Project name prefix for all resources"
  type        = string
  default     = "quantum-portal"
}

variable "db_password" {
  description = "PostgreSQL Flexible Server administrator password"
  type        = string
  sensitive   = true
}

variable "openai_sku" {
  description = "Azure OpenAI service SKU name"
  type        = string
  default     = "S0"
}

variable "aks_system_node_count" {
  description = "Initial node count for AKS system node pool"
  type        = number
  default     = 2
}

variable "aks_system_min_count" {
  description = "Minimum node count for AKS system node pool autoscaler"
  type        = number
  default     = 2
}

variable "aks_system_max_count" {
  description = "Maximum node count for AKS system node pool autoscaler"
  type        = number
  default     = 5
}

variable "aks_system_vm_size" {
  description = "VM size for AKS system node pool"
  type        = string
  default     = "Standard_D4s_v3" # 4 vCPU, 16 GB — handles 100 concurrent users
}

variable "aks_gpu_vm_size" {
  description = "VM size for AKS GPU node pool (Triton inference)"
  type        = string
  default     = "Standard_NC4as_T4_v3" # 1x NVIDIA T4, 4 vCPU, 28 GB
}

variable "aks_gpu_max_count" {
  description = "Maximum node count for AKS GPU node pool"
  type        = number
  default     = 3
}

variable "aks_kubernetes_version" {
  description = "Kubernetes version for AKS cluster"
  type        = string
  default     = "1.30"
}

variable "postgres_sku_name" {
  description = "SKU name for PostgreSQL Flexible Server"
  type        = string
  default     = "GP_Standard_D4s_v3" # 4 vCPU, 16 GB
}

variable "postgres_storage_mb" {
  description = "Storage capacity (MB) for PostgreSQL Flexible Server"
  type        = number
  default     = 131072 # 128 GB
}

variable "postgres_backup_retention_days" {
  description = "Backup retention period in days for PostgreSQL"
  type        = number
  default     = 30
}

variable "redis_capacity" {
  description = "Redis cache capacity (0=250MB, 1=1GB, 2=6GB, 3=13GB, 4=26GB, 5=53GB, 6=120GB)"
  type        = number
  default     = 2 # 6 GB — adequate for job queue + circuit result cache
}

variable "redis_family" {
  description = "Redis cache family (C=Basic/Standard, P=Premium)"
  type        = string
  default     = "C"
}

variable "redis_sku_name" {
  description = "Redis cache SKU: Basic, Standard, or Premium"
  type        = string
  default     = "Standard"
}

variable "storage_replication_type" {
  description = "Storage account replication type: LRS, GRS, ZRS, GZRS"
  type        = string
  default     = "GRS"
}

variable "log_analytics_retention_days" {
  description = "Log Analytics workspace data retention in days"
  type        = number
  default     = 30
}

variable "acr_sku" {
  description = "Azure Container Registry SKU: Basic, Standard, or Premium"
  type        = string
  default     = "Premium"
}

variable "key_vault_sku" {
  description = "Key Vault SKU: standard or premium"
  type        = string
  default     = "premium"
}

variable "vnet_address_space" {
  description = "Virtual network address space"
  type        = string
  default     = "10.0.0.0/16"
}

variable "aks_subnet_prefix" {
  description = "Subnet CIDR for AKS node pool"
  type        = string
  default     = "10.0.1.0/24"
}

variable "db_subnet_prefix" {
  description = "Subnet CIDR for PostgreSQL Flexible Server (delegated)"
  type        = string
  default     = "10.0.2.0/24"
}

variable "redis_subnet_prefix" {
  description = "Subnet CIDR for Redis private endpoint"
  type        = string
  default     = "10.0.3.0/24"
}

variable "aml_compute_instance_size" {
  description = "Azure ML compute instance VM size for notebook experiments"
  type        = string
  default     = "Standard_DS3_v2"
}
