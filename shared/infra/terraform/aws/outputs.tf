output "eks_cluster_name" {
  description = "EKS cluster name"
  value       = aws_eks_cluster.quantum_portal.name
}

output "eks_cluster_endpoint" {
  description = "EKS cluster API server endpoint"
  value       = aws_eks_cluster.quantum_portal.endpoint
  sensitive   = true
}

output "eks_cluster_ca" {
  description = "EKS cluster certificate authority data"
  value       = aws_eks_cluster.quantum_portal.certificate_authority[0].data
  sensitive   = true
}

output "ecr_portal_url" {
  description = "ECR URL for portal container image"
  value       = aws_ecr_repository.portal.repository_url
}

output "ecr_api_url" {
  description = "ECR URL for API container image"
  value       = aws_ecr_repository.api.repository_url
}

output "ecr_inference_url" {
  description = "ECR URL for inference container image"
  value       = aws_ecr_repository.inference.repository_url
}

output "rds_endpoint" {
  description = "RDS PostgreSQL endpoint"
  value       = aws_rds_instance.results_db.address
  sensitive   = true
}

output "rds_port" {
  description = "RDS PostgreSQL port"
  value       = aws_rds_instance.results_db.port
}

output "redis_primary_endpoint" {
  description = "ElastiCache Redis primary endpoint"
  value       = aws_elasticache_replication_group.job_queue.primary_endpoint_address
  sensitive   = true
}

output "datasets_bucket_name" {
  description = "S3 datasets bucket name"
  value       = aws_s3_bucket.quantum_datasets.bucket
}

output "cloudfront_domain" {
  description = "CloudFront distribution domain name"
  value       = aws_cloudfront_distribution.portal.domain_name
}

output "vpc_id" {
  description = "VPC ID"
  value       = aws_vpc.main.id
}

output "private_subnet_ids" {
  description = "Private subnet IDs"
  value       = aws_subnet.private[*].id
}

output "gpu_asg_name" {
  description = "GPU Auto Scaling Group name"
  value       = aws_autoscaling_group.gpu_inference.name
}
