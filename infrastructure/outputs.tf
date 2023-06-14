output "quay_rds_hostname" {
  description = "RDS instance hostname"
  value       = aws_db_instance.quay_db.address
  sensitive   = false
}

output "quay_rds_port" {
  description = "RDS instance port"
  value       = aws_db_instance.quay_db.port
  sensitive   = false
}

output "clair_rds_hostname" {
  description = "RDS instance hostname"
  value       = var.enable_clair ? aws_db_instance.clair_db[0].address : null
  sensitive   = false
}

output "clair_rds_port" {
  description = "RDS instance port"
  value       = var.enable_clair ? aws_db_instance.clair_db[0].port : null
  sensitive   = false
}

output "cf_singing_public_key_pem" {
  description = "CF signing public key"
  value       = data.tls_public_key.cloudfront_signing_public_key.public_key_pem
  sensitive   = false
}

output "build_redis_host" {
  description = "Builders Redis host"
  value = "${aws_elasticache_replication_group.quay_build_redis.primary_endpoint_address}"
  sensitive   = false
}

output "quay_hostname" {
  description = "Quay hostname"
  value = "${var.prefix}.${data.aws_route53_zone.zone.name}"
  sensitive   = false
}

output "prometheus_hostname" {
  description = "Prometheus hostname"
  value = var.enable_monitoring ? "prometheus-${var.prefix}.${data.aws_route53_zone.zone.name}" : null
  sensitive = false
}

output "prometheus_lb" {
  description = "Prometheus loadbalancer"
  value = var.enable_monitoring ? "${kubernetes_service.prometheus_lb_service[0].status.0.load_balancer.0.ingress.0.hostname}" : null
  sensitive = false

}

output "lb_name" {
  description = "Quay hostname"
  value = "${kubernetes_service.quay_lb_service.status.0.load_balancer.0.ingress.0.hostname}"
  sensitive   = false
}
