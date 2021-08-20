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
  default     = "us-west-1"
}

variable "quay_image" {
  description = "image to use for quay"
  type = string
  default = "quay.io/projectquay/quay@sha256:46334210eeb21aa6205215d1c4dbc40ea3381887c21a05d0bc47203c8f938987"
}

variable "clair_image" {
  description = "image to use for quay"
  type = string
  default = "quay.io/projectquay/clair@sha256:5fec3cf459159eabe2e4e1089687e25f638183a7e9bed1ecea8724e0597f8a14"
}

variable "rds_vpc_cidr" {
  description = "CIDR for the VPC where RDS is going to be created"
  type        = string
  default     = "172.33.0.0/16"
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
  default     = "vpc-0b2768f48c445b49f"
}

variable "openshift_route_suffix" {
  description = "Route suffix for the Openshift cluster"
  type        = string
  default     = "apps.quaydev-rosa-1.czz9.p1.openshiftapps.com"
}
