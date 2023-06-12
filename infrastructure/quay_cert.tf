resource "tls_private_key" "quay_lb_cert_key" {
  algorithm   = "ECDSA"
  ecdsa_curve = "P384"
}

resource "tls_self_signed_cert" "quay_lb_cert" {
  key_algorithm   = "ECDSA"
  private_key_pem = "${tls_private_key.quay_lb_cert_key.private_key_pem}"

  subject {
    common_name="${local.quay_hostname}"
    organization = "RedHat"
  }

  dns_names = ["${local.quay_hostname}"]
  is_ca_certificate=true
  validity_period_hours = 12000

  allowed_uses = [
    "key_encipherment",
    "digital_signature",
    "server_auth",
  ]
}

resource "aws_acm_certificate" "quay_domain_cert" {
  domain_name       = var.dns_domain 
  validation_method = "DNS"

  tags = {
    Environment = var.prefix
  }

  lifecycle {
    create_before_destroy = true
  }
}

resource "aws_route53_record" "quay_cert_validation_record" {
  for_each = {
    for dvo in aws_acm_certificate.quay_domain_cert.domain_validation_options : dvo.domain_name => {
      name   = dvo.resource_record_name
      record = dvo.resource_record_value
      type   = dvo.resource_record_type
    }
  }

  allow_overwrite = true
  name            = each.value.name
  records         = [each.value.record]
  ttl             = 60
  type            = each.value.type
  zone_id         = data.aws_route53_zone.zone.zone_id
}

resource "aws_acm_certificate_validation" "quay_cert_validation" {
  certificate_arn         = aws_acm_certificate.quay_domain_cert.arn
  validation_record_fqdns = [for record in aws_route53_record.quay_cert_validation_record : record.fqdn]
}