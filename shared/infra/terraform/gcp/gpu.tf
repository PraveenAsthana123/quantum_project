# =============================================================================
# Quantum Portal — GCP GPU Node Pools
# L4 for inference (always-available burst), H100 for heavy training (on-demand)
# =============================================================================

# ---------------------------------------------------------------------------
# L4 GPU node pool — inference (g2-standard-8, 1x L4, autoscale 0→3)
# Use case: vLLM (Gemma-2-9B), Triton inference, quantum simulation
# Cost: ~$1.10/hr per node; min=0 so idle cost is zero
# ---------------------------------------------------------------------------
resource "google_container_node_pool" "l4_inference" {
  provider   = google-beta
  name       = "l4-inference-${var.env}"
  cluster    = google_container_cluster.quantum_portal.name
  location   = var.region

  # Autopilot clusters manage node pools automatically;
  # for Standard clusters, remove the cluster.enable_autopilot block above
  # and this node_pool block becomes active as-is.
  # With Autopilot, GPU workloads are scheduled via pod resource requests +
  # tolerations and Autopilot auto-provisions the node — this file is
  # provided as the Standard cluster equivalent / reference config.

  autoscaling {
    min_node_count  = 0
    max_node_count  = 3
    location_policy = "BALANCED"
  }

  management {
    auto_repair  = true
    auto_upgrade = true
  }

  upgrade_settings {
    max_surge       = 1
    max_unavailable = 0
    strategy        = "SURGE"
  }

  node_config {
    machine_type = "g2-standard-8" # 8 vCPU, 32 GB RAM, 1x NVIDIA L4

    guest_accelerator {
      type               = "nvidia-l4"
      count              = 1
      gpu_driver_installation_config {
        gpu_driver_version = "LATEST"
      }
    }

    disk_size_gb = 200
    disk_type    = "pd-ssd"

    service_account = google_service_account.gke_sa.email

    oauth_scopes = [
      "https://www.googleapis.com/auth/cloud-platform",
    ]

    labels = {
      env              = var.env
      accelerator-type = "l4"
      workload         = "inference"
    }

    # Taint prevents non-GPU workloads from landing on expensive GPU nodes
    taint {
      key    = "nvidia.com/gpu"
      value  = "present"
      effect = "NO_SCHEDULE"
    }

    metadata = {
      disable-legacy-endpoints = "true"
    }

    shielded_instance_config {
      enable_secure_boot          = true
      enable_integrity_monitoring = true
    }
  }

  lifecycle {
    ignore_changes = [
      # Autopilot-managed fields
      node_config[0].resource_labels,
    ]
  }
}

# ---------------------------------------------------------------------------
# H100 burst node pool — large model training / complex QEC (a3-highgpu-8g)
# 8x H100 80GB SXM5 per node — on-demand, 0→1 autoscale
# Cost: ~$32/hr per node; min=0, only provisions when explicitly scheduled
# ---------------------------------------------------------------------------
resource "google_container_node_pool" "h100_burst" {
  provider   = google-beta
  name       = "h100-burst-${var.env}"
  cluster    = google_container_cluster.quantum_portal.name
  location   = var.zone # A3 machines are zonal, not regional

  autoscaling {
    min_node_count  = 0
    max_node_count  = 1 # single node = 8x H100; enough for burst fine-tuning
    location_policy = "ANY"
  }

  management {
    auto_repair  = true
    auto_upgrade = false # pin H100 pool; upgrades risk long drain on expensive hardware
  }

  node_config {
    machine_type = "a3-highgpu-8g" # 208 vCPU, 1872 GB RAM, 8x H100 80GB

    guest_accelerator {
      type  = "nvidia-h100-80gb"
      count = 8
      gpu_driver_installation_config {
        gpu_driver_version = "LATEST"
      }
    }

    disk_size_gb = 500
    disk_type    = "pd-ssd"

    service_account = google_service_account.gke_sa.email

    oauth_scopes = [
      "https://www.googleapis.com/auth/cloud-platform",
    ]

    labels = {
      env              = var.env
      accelerator-type = "h100"
      workload         = "training"
    }

    taint {
      key    = "nvidia.com/gpu"
      value  = "present"
      effect = "NO_SCHEDULE"
    }

    taint {
      key    = "workload"
      value  = "h100-training"
      effect = "NO_SCHEDULE"
    }

    metadata = {
      disable-legacy-endpoints = "true"
    }

    shielded_instance_config {
      enable_secure_boot          = true
      enable_integrity_monitoring = true
    }
  }
}

# ---------------------------------------------------------------------------
# CPU node pool — general workloads (quantum workers, API, portal)
# ---------------------------------------------------------------------------
resource "google_container_node_pool" "cpu_general" {
  name     = "cpu-general-${var.env}"
  cluster  = google_container_cluster.quantum_portal.name
  location = var.region

  autoscaling {
    min_node_count  = 2 # always-on for API + portal
    max_node_count  = 10
    location_policy = "BALANCED"
  }

  management {
    auto_repair  = true
    auto_upgrade = true
  }

  node_config {
    machine_type = "n2-standard-4" # 4 vCPU, 16 GB — handles 25+ pods per node

    disk_size_gb = 100
    disk_type    = "pd-balanced"

    service_account = google_service_account.gke_sa.email

    oauth_scopes = [
      "https://www.googleapis.com/auth/cloud-platform",
    ]

    labels = {
      env      = var.env
      workload = "general"
    }

    metadata = {
      disable-legacy-endpoints = "true"
    }

    shielded_instance_config {
      enable_secure_boot          = true
      enable_integrity_monitoring = true
    }
  }
}

# ---------------------------------------------------------------------------
# DCGM Exporter (GPU metrics → Prometheus)
# Applied as a Kubernetes DaemonSet via Helm; referenced here as comment.
# Deploy: helm upgrade --install dcgm-exporter \
#   nvidia/dcgm-exporter --namespace monitoring \
#   --set tolerations[0].key=nvidia.com/gpu \
#   --set tolerations[0].operator=Exists \
#   --set tolerations[0].effect=NoSchedule
# ---------------------------------------------------------------------------
