provider "acme" {
  # server_url = "https://acme-staging-v02.api.letsencrypt.org/directory"
  server_url = "https://acme-v02.api.letsencrypt.org/directory"
}

resource "tls_private_key" "quay_private_key"{
  algorithm = "RSA"
}

resource "acme_registration" "quay_registration" {
  account_key_pem = tls_private_key.quay_private_key.private_key_pem
  email_address = "${var.email_address}"
}

resource "acme_certificate" "quay_cert" {
  account_key_pem = acme_registration.quay_registration.account_key_pem
  common_name = aws_route53_record.quay_hostname.name
  subject_alternative_names = ["*.${aws_route53_record.quay_hostname.name}"]
  disable_complete_propagation = true

  dns_challenge {
    provider = "route53"
  }

  depends_on = [acme_registration.quay_registration]
}

resource "aws_acm_certificate" "quay_letsencrypt_cert" {
  certificate_body = acme_certificate.quay_cert.certificate_pem
  private_key = acme_certificate.quay_cert.private_key_pem
  certificate_chain = acme_certificate.quay_cert.issuer_pem
}

