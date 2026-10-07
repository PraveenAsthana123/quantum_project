# =============================================================================
# Quantum Portal — AWS GPU Node Group
# g4dn.xlarge (T4 GPU) Spot instances for inference workloads
# =============================================================================

data "aws_ssm_parameter" "eks_gpu_ami" {
  name = "/aws/service/eks/optimized-ami/${aws_eks_cluster.quantum_portal.version}/amazon-linux-2-gpu/recommended/image_id"
}

# ---------------------------------------------------------------------------
# Security Group for GPU nodes
# ---------------------------------------------------------------------------
resource "aws_security_group" "gpu_nodes" {
  name        = "${var.project_name}-gpu-nodes-sg-${var.env}"
  description = "Security group for GPU inference nodes"
  vpc_id      = aws_vpc.main.id

  ingress {
    from_port       = 0
    to_port         = 0
    protocol        = "-1"
    security_groups = [aws_security_group.eks_cluster.id]
    description     = "Allow all traffic from EKS control plane"
  }

  ingress {
    from_port = 0
    to_port   = 0
    protocol  = "-1"
    self      = true
    description = "Allow node-to-node communication"
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name = "${var.project_name}-gpu-nodes-sg-${var.env}"
  }
}

# ---------------------------------------------------------------------------
# Launch Template for g4dn.xlarge (1x T4 GPU, 4 vCPU, 16 GB)
# Spot pricing: ~$0.16/hr vs $0.526/hr on-demand (70% savings)
# ---------------------------------------------------------------------------
resource "aws_launch_template" "gpu_inference" {
  name_prefix   = "${var.project_name}-gpu-lt-"
  image_id      = data.aws_ssm_parameter.eks_gpu_ami.value
  instance_type = "g4dn.xlarge"

  # Spot instance configuration
  instance_market_options {
    market_type = "spot"
    spot_options {
      max_price          = "0.20" # max $0.20/hr — allows spot pool flexibility
      spot_instance_type = "persistent"
      instance_interruption_behavior = "stop"
    }
  }

  block_device_mappings {
    device_name = "/dev/xvda"
    ebs {
      volume_size           = 200
      volume_type           = "gp3"
      iops                  = 3000
      throughput            = 125
      encrypted             = true
      kms_key_id            = aws_kms_key.eks.arn
      delete_on_termination = true
    }
  }

  vpc_security_group_ids = [
    aws_security_group.eks_cluster.id,
    aws_security_group.gpu_nodes.id,
  ]

  iam_instance_profile {
    arn = aws_iam_instance_profile.gpu_nodes.arn
  }

  user_data = base64encode(<<-EOF
    #!/bin/bash
    set -ex

    # Bootstrap EKS node with GPU support
    /etc/eks/bootstrap.sh ${aws_eks_cluster.quantum_portal.name} \
      --kubelet-extra-args \
      '--node-labels=workload=inference,accelerator=t4 --register-with-taints=nvidia.com/gpu=present:NoSchedule'

    # Install NVIDIA device plugin dependencies (handled by DaemonSet, but ensure drivers loaded)
    nvidia-smi || true
  EOF
  )

  metadata_options {
    http_endpoint               = "enabled"
    http_tokens                 = "required" # IMDSv2 only
    http_put_response_hop_limit = 2
  }

  tag_specifications {
    resource_type = "instance"
    tags = {
      Name        = "${var.project_name}-gpu-node-${var.env}"
      Environment = var.env
      Workload    = "inference"
    }
  }

  lifecycle {
    create_before_destroy = true
  }
}

# IAM instance profile for GPU nodes
resource "aws_iam_instance_profile" "gpu_nodes" {
  name = "${var.project_name}-gpu-node-profile-${var.env}"
  role = aws_iam_role.eks_nodes.name
}

# ---------------------------------------------------------------------------
# Auto Scaling Group for GPU inference nodes (0 → 3 nodes)
# Scale-to-zero when no inference workload; scale-up via Karpenter or KEDA
# ---------------------------------------------------------------------------
resource "aws_autoscaling_group" "gpu_inference" {
  name                = "${var.project_name}-gpu-asg-${var.env}"
  min_size            = 0
  max_size            = 3
  desired_capacity    = 0 # start at zero; scaled by Karpenter
  vpc_zone_identifier = aws_subnet.private[*].id

  mixed_instances_policy {
    instances_distribution {
      on_demand_base_capacity                  = 0
      on_demand_percentage_above_base_capacity = 0 # 100% spot
      spot_allocation_strategy                 = "capacity-optimized"
    }

    launch_template {
      launch_template_specification {
        launch_template_id = aws_launch_template.gpu_inference.id
        version            = "$Latest"
      }

      # Fallback instance types if g4dn.xlarge spot unavailable
      override {
        instance_type = "g4dn.xlarge"
      }
      override {
        instance_type = "g4dn.2xlarge"
      }
      override {
        instance_type = "g5.xlarge"
      }
    }
  }

  health_check_type         = "EC2"
  health_check_grace_period = 300

  instance_refresh {
    strategy = "Rolling"
    preferences {
      min_healthy_percentage = 50
    }
  }

  tag {
    key                 = "Name"
    value               = "${var.project_name}-gpu-node-${var.env}"
    propagate_at_launch = true
  }

  tag {
    key                 = "kubernetes.io/cluster/${aws_eks_cluster.quantum_portal.name}"
    value               = "owned"
    propagate_at_launch = true
  }

  tag {
    key                 = "k8s.io/cluster-autoscaler/enabled"
    value               = "true"
    propagate_at_launch = true
  }

  tag {
    key                 = "k8s.io/cluster-autoscaler/${aws_eks_cluster.quantum_portal.name}"
    value               = "owned"
    propagate_at_launch = true
  }

  lifecycle {
    ignore_changes = [desired_capacity] # managed by Cluster Autoscaler / Karpenter
  }
}

# ---------------------------------------------------------------------------
# CloudWatch alarm — spot interruption notice via EventBridge
# Sends notification to SNS when GPU spot node will be interrupted in 2 min
# ---------------------------------------------------------------------------
resource "aws_cloudwatch_event_rule" "spot_interruption" {
  name        = "${var.project_name}-spot-interruption-${var.env}"
  description = "Capture EC2 Spot Instance interruption warnings for GPU nodes"

  event_pattern = jsonencode({
    "source"      = ["aws.ec2"]
    "detail-type" = ["EC2 Spot Instance Interruption Warning"]
    "detail" = {
      "instance-id" = [{ "prefix" = "" }]
    }
  })
}

resource "aws_sns_topic" "spot_interruption" {
  name = "${var.project_name}-spot-interruption-${var.env}"
}

resource "aws_cloudwatch_event_target" "spot_interruption_sns" {
  rule      = aws_cloudwatch_event_rule.spot_interruption.name
  target_id = "SpotInterruptionSNS"
  arn       = aws_sns_topic.spot_interruption.arn
}
