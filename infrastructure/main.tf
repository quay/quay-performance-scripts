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
}

data "template_file" "quay_template" {
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

    registry_state = local.is_secondary == 1 ? "readonly" : "normal"
  }
}

resource "local_file" "quay_deployment" {
  content = data.template_file.quay_template.rendered
  filename = "${var.prefix}_quay_deployment.yaml"
}
