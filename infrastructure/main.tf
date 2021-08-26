provider "aws" {
  region = var.region
  profile = var.aws_profile
}

data "aws_availability_zones" "available" {}

locals {
  quay_endpoint = "quay-app-${var.prefix}.${var.openshift_route_suffix}"
}

resource "tls_private_key" "quay_ssl_key" {
  algorithm   = "ECDSA"
  ecdsa_curve = "P384"
}

resource "tls_self_signed_cert" "quay_ssl_cert" {
  key_algorithm   = "ECDSA"
  private_key_pem = "${tls_private_key.quay_ssl_key.private_key_pem}"

  subject {
    common_name="${local.quay_endpoint}"
    organization = "RedHat"
  }

  uris= ["${local.quay_endpoint}"]
  is_ca_certificate=true
  validity_period_hours = 12000

  allowed_uses = [
    "key_encipherment",
    "digital_signature",
    "server_auth",
  ]
}

data "template_file" "quay_template" {
  template = "${file("${path.module}/quay_deployment.yaml.tpl")}"
  vars = {
    namespace = "${var.prefix}-quay"
    replicas = 1
    quay_image = "${var.quay_image}"
    quay_route_host = "${local.quay_endpoint}"

    redis_host = "${aws_elasticache_replication_group.quay_build_redis.primary_endpoint_address}"
    redis_port = "6379"
    redis_password = "${var.db_password}"

    db_user = "${aws_db_instance.quay_db.username}"
    db_password = "${var.db_password}"
    db_host = "${aws_db_instance.quay_db.address}"
    db_port = 3306

    s3_secret_key = "${aws_iam_access_key.s3_access_key.secret}"
    s3_access_key_id = "${aws_iam_access_key.s3_access_key.id}"
    s3_bucket_name = "${aws_s3_bucket.quay_s3_storage.bucket}"

    cloudfront_signing_key_pem = "${indent(4, tls_private_key.cloudfront_signing_private_key.private_key_pem)}"
    cloudfront_key_id = "${aws_cloudfront_public_key.quay_cloudfront_public_key.id}"
    cloudfront_distribution_domain = "${aws_cloudfront_distribution.s3_distribution.domain_name}"

    ssl_key = "${indent(4, tls_private_key.quay_ssl_key.private_key_pem)}"
    ssl_cert = "${indent(4, tls_self_signed_cert.quay_ssl_cert.cert_pem)}"

    clair_image = "${var.clair_image}"

    clair_db_host = "${aws_db_instance.clair_db.address}"
    clair_db_port = "${aws_db_instance.clair_db.port}"
    clair_db_user = "${aws_db_instance.clair_db.username}"
    clair_db_password = "${var.db_password}"

    clair_auth_psk = base64encode("clairsharedpassword")
    clair_replicas = 1
  }
}

resource "local_file" "quay_deployment" {
  content = data.template_file.quay_template.rendered
  filename = "${var.prefix}_quay_deployment.yaml"
}
