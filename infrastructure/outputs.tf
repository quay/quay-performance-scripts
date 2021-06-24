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
  value       = aws_db_instance.clair_db.address
  sensitive   = false
}

output "clair_rds_port" {
  description = "RDS instance port"
  value       = aws_db_instance.clair_db.port
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