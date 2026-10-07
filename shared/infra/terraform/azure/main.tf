terraform {
  required_version = ">= 1.7.0"

  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "~> 3.100"
    }
    azuread = {
      source  = "hashicorp/azuread"
      version = "~> 2.50"
    }
  }

  backend "azurerm" {
    # resource_group_name  = "<set via -backend-config>"
    # storage_account_name = "<set via -backend-config>"
    # container_name       = "tfstate"
    # key                  = "quantum-portal.terraform.tfstate"
  }
}

provider "azurerm" {
  features {
    resource_group {
      prevent_deletion_if_contains_resources = true
    }
    key_vault {
      purge_soft_delete_on_destroy    = false
      recover_soft_deleted_key_vaults = true
    }
  }
}

# =============================================================================
# Variables
# =============================================================================
variable "env" {
  type    = string
  default = "prod"
  validation {
    condition     = contains(["prod", "staging", "dev"], var.env)
    error_message = "env must be prod, staging, or dev."
  }
}

variable "location" {
  type    = string
  default = "eastus"
}

variable "db_password" {
  type      = string
  sensitive = true
}

variable "openai_sku" {
  type    = string
  default = "S0"
}

# =============================================================================
# Resource Group
# =============================================================================
resource "azurerm_resource_group" "quantum" {
  name     = "rg-quantum-portal-${var.env}"
  location = var.location

  tags = {
    Environment = var.env
    Project     = "quantum-portal"
    ManagedBy   = "terraform"
  }
}

# =============================================================================
# Virtual Network
# =============================================================================
resource "azurerm_virtual_network" "quantum" {
  name                = "vnet-quantum-${var.env}"
  address_space       = ["10.0.0.0/16"]
  location            = azurerm_resource_group.quantum.location
  resource_group_name = azurerm_resource_group.quantum.name
}

resource "azurerm_subnet" "aks" {
  name                 = "snet-aks-${var.env}"
  resource_group_name  = azurerm_resource_group.quantum.name
  virtual_network_name = azurerm_virtual_network.quantum.name
  address_prefixes     = ["10.0.1.0/24"]
}

resource "azurerm_subnet" "db" {
  name                 = "snet-db-${var.env}"
  resource_group_name  = azurerm_resource_group.quantum.name
  virtual_network_name = azurerm_virtual_network.quantum.name
  address_prefixes     = ["10.0.2.0/24"]

  delegation {
    name = "postgres-delegation"
    service_delegation {
      name    = "Microsoft.DBforPostgreSQL/flexibleServers"
      actions = ["Microsoft.Network/virtualNetworks/subnets/join/action"]
    }
  }
}

resource "azurerm_subnet" "redis" {
  name                 = "snet-redis-${var.env}"
  resource_group_name  = azurerm_resource_group.quantum.name
  virtual_network_name = azurerm_virtual_network.quantum.name
  address_prefixes     = ["10.0.3.0/24"]
}

# =============================================================================
# Key Vault — secrets + key management
# =============================================================================
data "azurerm_client_config" "current" {}

resource "azurerm_key_vault" "quantum" {
  name                        = "kv-quantum-${var.env}-${substr(md5(azurerm_resource_group.quantum.id), 0, 6)}"
  location                    = azurerm_resource_group.quantum.location
  resource_group_name         = azurerm_resource_group.quantum.name
  sku_name                    = "premium"
  tenant_id                   = data.azurerm_client_config.current.tenant_id
  enable_rbac_authorization   = true
  purge_protection_enabled    = true
  soft_delete_retention_days  = 30

  network_acls {
    default_action = "Deny"
    bypass         = "AzureServices"
    ip_rules       = [] # add admin IPs here
    virtual_network_subnet_ids = [azurerm_subnet.aks.id]
  }
}

resource "azurerm_key_vault_secret" "db_password" {
  name         = "quantum-db-password"
  value        = var.db_password
  key_vault_id = azurerm_key_vault.quantum.id
}

# =============================================================================
# AKS Cluster
# =============================================================================
resource "azurerm_user_assigned_identity" "aks" {
  name                = "id-aks-quantum-${var.env}"
  location            = azurerm_resource_group.quantum.location
  resource_group_name = azurerm_resource_group.quantum.name
}

resource "azurerm_kubernetes_cluster" "quantum_portal" {
  name                = "aks-quantum-${var.env}"
  location            = azurerm_resource_group.quantum.location
  resource_group_name = azurerm_resource_group.quantum.name
  dns_prefix          = "quantum-${var.env}"
  kubernetes_version  = "1.30"

  sku_tier = var.env == "prod" ? "Standard" : "Free"

  default_node_pool {
    name                 = "system"
    node_count           = 2
    vm_size              = "Standard_D4s_v3" # 4 vCPU, 16 GB
    os_disk_size_gb      = 128
    os_disk_type         = "Managed"
    vnet_subnet_id       = azurerm_subnet.aks.id
    enable_auto_scaling  = true
    min_count            = 2
    max_count            = 4
    type                 = "VirtualMachineScaleSets"
    only_critical_addons_enabled = false

    upgrade_settings {
      max_surge = "33%"
    }
  }

  identity {
    type         = "UserAssigned"
    identity_ids = [azurerm_user_assigned_identity.aks.id]
  }

  network_profile {
    network_plugin     = "azure"
    network_policy     = "calico"
    load_balancer_sku  = "standard"
    service_cidr       = "172.16.0.0/16"
    dns_service_ip     = "172.16.0.10"
  }

  key_vault_secrets_provider {
    secret_rotation_enabled  = true
    secret_rotation_interval = "2m"
  }

  oms_agent {
    log_analytics_workspace_id = azurerm_log_analytics_workspace.quantum.id
  }

  microsoft_defender {
    log_analytics_workspace_id = azurerm_log_analytics_workspace.quantum.id
  }

  azure_active_directory_role_based_access_control {
    managed            = true
    azure_rbac_enabled = true
  }

  tags = {
    Environment = var.env
  }
}

# GPU node pool — Standard_NC4as_T4_v3 (1x T4, 4 vCPU, 28 GB)
resource "azurerm_kubernetes_cluster_node_pool" "gpu" {
  name                  = "gpu"
  kubernetes_cluster_id = azurerm_kubernetes_cluster.quantum_portal.id
  vm_size               = "Standard_NC4as_T4_v3"
  os_disk_size_gb       = 200
  vnet_subnet_id        = azurerm_subnet.aks.id
  enable_auto_scaling   = true
  min_count             = 0
  max_count             = 3
  node_count            = 0

  node_labels = {
    "workload"         = "inference"
    "accelerator-type" = "t4"
  }

  node_taints = ["nvidia.com/gpu=present:NoSchedule"]

  tags = {
    Environment = var.env
    Workload    = "inference"
  }
}

# =============================================================================
# Container Registry
# =============================================================================
resource "azurerm_container_registry" "quantum_acr" {
  name                = "acrquantum${var.env}${substr(md5(azurerm_resource_group.quantum.id), 0, 4)}"
  resource_group_name = azurerm_resource_group.quantum.name
  location            = azurerm_resource_group.quantum.location
  sku                 = var.env == "prod" ? "Premium" : "Basic"
  admin_enabled       = false

  encryption {
    enabled            = var.env == "prod"
    # key_vault_key_id = azurerm_key_vault_key.acr.id  # uncomment with premium+key
  }

  # Geo-replication for prod (Premium SKU)
  dynamic "georeplications" {
    for_each = var.env == "prod" ? ["westus"] : []
    content {
      location                  = georeplications.value
      zone_redundancy_enabled   = true
    }
  }
}

# Grant AKS pull access to ACR
resource "azurerm_role_assignment" "aks_acr_pull" {
  principal_id                     = azurerm_kubernetes_cluster.quantum_portal.kubelet_identity[0].object_id
  role_definition_name             = "AcrPull"
  scope                            = azurerm_container_registry.quantum_acr.id
  skip_service_principal_aad_check = true
}

# =============================================================================
# PostgreSQL Flexible Server
# =============================================================================
resource "azurerm_private_dns_zone" "postgres" {
  name                = "quantum-${var.env}.private.postgres.database.azure.com"
  resource_group_name = azurerm_resource_group.quantum.name
}

resource "azurerm_private_dns_zone_virtual_network_link" "postgres" {
  name                  = "postgres-vnet-link"
  private_dns_zone_name = azurerm_private_dns_zone.postgres.name
  virtual_network_id    = azurerm_virtual_network.quantum.id
  resource_group_name   = azurerm_resource_group.quantum.name
}

resource "azurerm_postgresql_flexible_server" "results_db" {
  name                   = "psql-quantum-${var.env}"
  resource_group_name    = azurerm_resource_group.quantum.name
  location               = azurerm_resource_group.quantum.location
  version                = "16"
  delegated_subnet_id    = azurerm_subnet.db.id
  private_dns_zone_id    = azurerm_private_dns_zone.postgres.id
  administrator_login    = "quantum_admin"
  administrator_password = var.db_password
  zone                   = "1"

  sku_name   = "GP_Standard_D4s_v3" # 4 vCPU, 16 GB
  storage_mb = 131072 # 128 GB

  high_availability {
    mode                      = var.env == "prod" ? "ZoneRedundant" : "Disabled"
    standby_availability_zone = var.env == "prod" ? "2" : null
  }

  backup_retention_days        = 30
  geo_redundant_backup_enabled = var.env == "prod"

  maintenance_window {
    day_of_week  = 0 # Sunday
    start_hour   = 2
    start_minute = 0
  }

  authentication {
    password_auth_enabled         = true
    active_directory_auth_enabled = false
  }

  depends_on = [azurerm_private_dns_zone_virtual_network_link.postgres]
}

resource "azurerm_postgresql_flexible_server_database" "quantum_results" {
  name      = "quantum_results"
  server_id = azurerm_postgresql_flexible_server.results_db.id
  collation = "en_US.utf8"
  charset   = "UTF8"
}

# =============================================================================
# Azure Cache for Redis
# =============================================================================
resource "azurerm_redis_cache" "job_queue" {
  name                = "redis-quantum-${var.env}"
  location            = azurerm_resource_group.quantum.location
  resource_group_name = azurerm_resource_group.quantum.name
  capacity            = 2 # 6 GB cache
  family              = "C"
  sku_name            = var.env == "prod" ? "Standard" : "Basic"
  enable_non_ssl_port = false
  minimum_tls_version = "1.2"

  redis_configuration {
    maxmemory_reserved = 125
    maxmemory_delta    = 125
    maxmemory_policy   = "allkeys-lru"
  }

  patch_schedule {
    day_of_week = "Sunday"
    start_hour_utc = 2
  }
}

# =============================================================================
# Storage Account — datasets
# =============================================================================
resource "azurerm_storage_account" "quantum_datasets" {
  name                     = "stquantum${var.env}${substr(md5(azurerm_resource_group.quantum.id), 0, 6)}"
  resource_group_name      = azurerm_resource_group.quantum.name
  location                 = azurerm_resource_group.quantum.location
  account_tier             = "Standard"
  account_replication_type = var.env == "prod" ? "GRS" : "LRS"
  account_kind             = "StorageV2"
  access_tier              = "Cool"

  https_traffic_only_enabled    = true
  min_tls_version               = "TLS1_2"
  allow_nested_items_to_be_public = false

  blob_properties {
    versioning_enabled = true

    delete_retention_policy {
      days = 30
    }

    container_delete_retention_policy {
      days = 7
    }
  }

  identity {
    type = "SystemAssigned"
  }
}

resource "azurerm_storage_container" "datasets" {
  name                  = "datasets"
  storage_account_name  = azurerm_storage_account.quantum_datasets.name
  container_access_type = "private"
}

resource "azurerm_storage_container" "mlflow_artifacts" {
  name                  = "mlflow-artifacts"
  storage_account_name  = azurerm_storage_account.quantum_datasets.name
  container_access_type = "private"
}

# =============================================================================
# Azure OpenAI Service
# =============================================================================
resource "azurerm_cognitive_account" "openai" {
  name                = "openai-quantum-${var.env}"
  location            = "eastus" # Azure OpenAI available regions are limited
  resource_group_name = azurerm_resource_group.quantum.name
  kind                = "OpenAI"
  sku_name            = var.openai_sku

  custom_subdomain_name = "quantum-${var.env}-${substr(md5(azurerm_resource_group.quantum.id), 0, 6)}"

  network_acls {
    default_action = "Deny"
    virtual_network_rules {
      subnet_id = azurerm_subnet.aks.id
    }
  }

  identity {
    type = "SystemAssigned"
  }
}

# Deploy GPT-4o model (available in eastus)
resource "azurerm_cognitive_deployment" "gpt4o" {
  name                 = "gpt-4o"
  cognitive_account_id = azurerm_cognitive_account.openai.id

  model {
    format  = "OpenAI"
    name    = "gpt-4o"
    version = "2024-05-13"
  }

  scale {
    type     = "Standard"
    capacity = 10 # 10K tokens per minute
  }
}

# =============================================================================
# Log Analytics + Monitor
# =============================================================================
resource "azurerm_log_analytics_workspace" "quantum" {
  name                = "law-quantum-${var.env}"
  location            = azurerm_resource_group.quantum.location
  resource_group_name = azurerm_resource_group.quantum.name
  sku                 = "PerGB2018"
  retention_in_days   = 30
}

# =============================================================================
# Outputs
# =============================================================================
output "aks_cluster_name" {
  value = azurerm_kubernetes_cluster.quantum_portal.name
}

output "aks_kube_config" {
  value     = azurerm_kubernetes_cluster.quantum_portal.kube_config_raw
  sensitive = true
}

output "acr_login_server" {
  value = azurerm_container_registry.quantum_acr.login_server
}

output "postgres_fqdn" {
  value     = azurerm_postgresql_flexible_server.results_db.fqdn
  sensitive = true
}

output "redis_hostname" {
  value     = azurerm_redis_cache.job_queue.hostname
  sensitive = true
}

output "storage_account_name" {
  value = azurerm_storage_account.quantum_datasets.name
}

output "openai_endpoint" {
  value = azurerm_cognitive_account.openai.endpoint
}
