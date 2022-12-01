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

variable "region" {
  description = "Region to deploy resources"
  type        = string
  default     = "us-east-1"
}

variable "quay_image" {
  description = "image to use for quay"
  type = string
  default = "quay.io/projectquay/quay:latest
}

variable "clair_image" {
  description = "image to use for quay"
  type = string
  default = "quay.io/projectquay/clair:nightly
}

variable "enable_clair" {
  description = "Enable Clair (creates required resources)"
  type        = bool
  default     = false
}

variable "rds_vpc_cidr" {
  description = "CIDR for the VPC where RDS is going to be created"
  type        = string
  default     = "172.31.0.0/16"
}

variable "openshift_cidrs" {
  description = "CIDR for openshift access to RDS"
  type        = list
  default     = ["10.0.0.0/8", "172.30.0.0/16"]
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

variable "quay_db_multi_az" {
  description = "Enable multi az"
  type = bool
  default = false
}
