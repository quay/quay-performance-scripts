variable "prefix" {
  description = "Prefix for instances"
  type        = string
  default     = "perftest1"
}

variable "aws_profile" {
  description = "AWS profile used for deployment"
  type        = string
  default     = "default"
}

variable "deploy_type" {
  description = "Primary or secondary"
  type = string
  default = "primary"
}

variable "region" {
  description = "Primary AWS region"
  type = string
  default = "us-east-1"
}

variable "primary_s3_bucket_arn" {
  description = "ARN of the primary bucket"
  type = string
  default = ""
}

variable "primary_db_arn" {
  description = "ARN of the primary DB"
  type = string
  default = ""
}

variable "quay_image" {
  description = "image to use for quay"
  type = string
  default = "quay.io/projectquay/quay:latest"
}

variable "clair_image" {
  description = "image to use for quay"
  type = string
  default = "quay.io/projectquay/clair:nightly"
}

variable "enable_clair" {
  description = "Enable Clair (creates required resources)"
  type        = bool
  default     = false
}

variable "quay_vpc_cidr" {
  description = "CIDR for the VPC where RDS is going to be created"
  type        = string
  default     = "172.31.0.0/16"
}

variable "openshift_cidrs" {
  description = "CIDR for openshift access to RDS"
  type        = list
  default     = ["10.0.0.0/8"]
}

variable "db_password" {
  description = "Password for Clair and Quay DB"
  type        = string
  sensitive   = true
}

variable "openshift_vpc_id" {
  description = "VPC ID of the openshift cluster"
  type        = string
  default     = "vpc-0708b20c341aeb3d0"
}

variable "openshift_route_suffix" {
  description = "Route suffix for the Openshift cluster"
  type        = string
  default     = "apps.quaydev-rosa.cv2k.p1.openshiftapps.com"
}

variable "builder_ssh_keypair" {
  description = "SSH keypair for builders"
  type        = string
  default     = "syed-quaydev-ssh-keypair"
}

variable "builder_access_key" {
  description = "Access key for builder"
  type        = string
  default     = ""
}

variable "builder_secret_key" {
  description = "secret key for builder"
  type        = string
  default     = ""
}

variable "dns_domain" {
  description = "Domain used to reach the endpoint (set as SERVER_HOSTNAME)"
  type        = string
  default     = "quaydev.org."
}

variable "dns_zone" {
  description = "Domain used to reach the endpoint (set as SERVER_HOSTNAME)"
  type        = string
  default     = "quaydev.org."
}

variable "quay_db_multi_az" {
  description = "Enable multi az"
  type = bool
  default = false
}

variable "kube_context" {
  description = "Context for the kubernetes connection"
  type = string
  default = "default"
}

variable "redis_azs" {
  description = "Redis availability zones"
  type = list
  default = ["us-east-1a", "us-east-1b"]
}

variable "enable_monitoring" {
  description = "enable prometheus/grafana monitoring for quay"
  type = bool
  default = false
}

variable "prometheus_image" {
  description = "image for prometheus container"
  type = string
  default = "prom/prometheus"
}

variable "grafana_image" {
  description = "image for grafana container"
  type = string
  default = "grafana/grafana"
}

variable "quay_db_version" {
  description = "version of quay's database"
  type = string
  default = "5.7.41"
}

variable "clair_db_version" {
  description = "version of clair's database"
  type = string
  default = "14.2"
}

variable "service_key_kid_path" {
  description = "Path to the service key kid for the secondary environment generated after running the setup_service_keys script"
  type = string
  default = ""
}

variable "service_key_pem_path" {
  description = "Path to the service key pem for the secondary environment generated after running the setup_service_keys script"
  type = string
  default = ""
}
