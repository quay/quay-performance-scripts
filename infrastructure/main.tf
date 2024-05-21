terraform {
  required_providers {
    aws  = {
      version = "5.24.0"
    }
    tls = {
      source = "hashicorp/tls"
      version = "4.0.4"
    }
    cloudinit = {
      source = "hashicorp/cloudinit"
      version = "2.3.2"
    }
  }
}

provider "aws" {
  region = var.region
  profile = var.aws_profile
}

provider "kubernetes" {
  config_path    = "~/.kube/config"
  config_context = "${var.kube_context}"
}

resource "kubernetes_namespace" "quay_ns" {
  metadata {
    name = "${var.prefix}-quay"
  }
}

data "aws_availability_zones" "available" {}

locals {
    quay_route_endpoint = "oauth-openshift.${var.openshift_route_suffix}"
    quay_hostname = "${var.prefix}.${data.aws_route53_zone.zone.name}"
    is_primary = var.deploy_type == "primary"
    is_secondary = var.deploy_type == "secondary"
}

data "http" "genkeyscript" {
  url = "https://raw.githubusercontent.com/quay/quay/master/tools/generatekeypair.py"
}

resource "null_resource" "update_service_key" {
  count = local.is_secondary ? 1 : 0
  provisioner "local-exec" {
    command = <<EOT
      python -m venv venv
      source venv/bin/activate
      pip install -r requirements-generatekeys.txt

      # Generate quay-readonly.pem, quay-readonly.kid, and quay-readonly.jwk
      python -c '${data.http.genkeyscript.body}' quay-readonly

      # Write out SQL commands for updating service keys
      sed -e "s/QUAY_READONLY_KID/$(cat quay-readonly.kid)/g" \
        -e "s/QUAY_READONLY_JWK/$(cat quay-readonly.jwk)/g" \
        update_service_keys.sql.template > update_service_keys.sql

      # Run script to update service keys
      PGPASSWORD=${var.primary_db_password} psql -U quay -h ${var.primary_db_hostname} < update_service_keys.sql
    EOT
  }
}

data "local_file" "key" {
  count = local.is_secondary ? 1 : 0
  depends_on = [null_resource.update_service_key]
  filename = "quay-readonly.jwk"
}

data "local_file" "cert" {
  count = local.is_secondary ? 1 : 0
  depends_on = [null_resource.update_service_key]
  filename = "quay-readonly.pem"
}

data "local_file" "key_id" {
  count = local.is_secondary ? 1 : 0
  depends_on = [null_resource.update_service_key]
  filename = "quay-readonly.kid"
}

data "template_file" "quay_template" {
  depends_on = [data.local_file.key, data.local_file.cert, data.local_file.key_id]
  template = "${file("${path.module}/quay_deployment.yaml.tpl")}"
  vars = {
    namespace = "${var.prefix}-quay"

    region = "${var.region}"
    replicas = 1
    quay_image = "${var.quay_image}"
    quay_route_host = "${var.dns_domain}"

    redis_host = "${aws_elasticache_replication_group.quay_build_redis.primary_endpoint_address}"
    redis_port = "6379"
    redis_password = "${var.db_password}"

    db_user = "${aws_rds_cluster.quay_db.master_username}"
    db_password = "${var.db_password}"
    db_host = "${aws_rds_cluster.quay_db.endpoint}"
    db_port = 5432

    s3_secret_key = "${aws_iam_access_key.s3_access_key.secret}"
    s3_access_key_id = "${aws_iam_access_key.s3_access_key.id}"
    s3_bucket_name = "${aws_s3_bucket.quay_s3_storage.bucket}"

    cloudfront_signing_key_pem = "${indent(4, tls_private_key.cloudfront_signing_private_key.private_key_pem)}"
    cloudfront_key_id = "${aws_cloudfront_public_key.quay_cloudfront_public_key.id}"
    cloudfront_distribution_domain = "${aws_cloudfront_distribution.s3_distribution.domain_name}"

    ssl_key = "${indent(4, tls_private_key.quay_lb_cert_key.private_key_pem)}"
    ssl_cert = "${indent(4, tls_self_signed_cert.quay_lb_cert.cert_pem)}"

    enable_clair = var.enable_clair
    clair_image = "${var.clair_image}"

    clair_db_host = var.enable_clair ? "${aws_db_instance.clair_db[0].address}" : null
    clair_db_port = var.enable_clair ? "${aws_db_instance.clair_db[0].port}" : null
    clair_db_user = var.enable_clair ? "${aws_db_instance.clair_db[0].username}" : null
    clair_db_password = "${var.db_password}"

    clair_auth_psk = base64encode("clairsharedpassword")
    clair_replicas = 1

    builder_access_key = "${var.builder_access_key}"
    builder_secret_key = "${var.builder_secret_key}"
    builder_security_group_id = "${aws_security_group.db_security_group.id}"
    builder_subnet_id = "${module.quay_vpc.public_subnets[0]}"
    builder_ssh_keypair = "${var.builder_ssh_keypair}"

    registry_state = local.is_secondary ? "readonly" : "normal"

    enable_monitoring = var.enable_monitoring
    prometheus_image = "${var.prometheus_image}"
    grafana_image = "${var.grafana_image}"
    prometheus_host = var.enable_monitoring ? "prometheus-${var.prefix}.${data.aws_route53_zone.zone.name}" : ""

    service_key_kid = local.is_secondary ? "${indent(4, data.local_file.key_id[0].content)}" : ""
    service_key_pem = local.is_secondary ? "${indent(4, data.local_file.cert[0].content)}" : ""
    is_secondary = local.is_secondary
  }
}

resource "local_file" "quay_deployment" {
  content = data.template_file.quay_template.rendered
  filename = "${var.prefix}_quay_deployment.yaml"
}

resource "null_resource" "clean" {
  provisioner "local-exec" {
    when    = destroy
    command = "rm -f quay-readonly.pem quay-readonly.kid quay-readonly.jwk update_service_keys.sql"
  }
}
