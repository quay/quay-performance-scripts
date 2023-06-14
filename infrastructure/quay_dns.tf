
data "aws_route53_zone" "zone" {
  name         = "${var.dns_zone}"
  private_zone = false
}

resource "aws_route53_record" "quay" {
  zone_id = data.aws_route53_zone.zone.zone_id
  name    = "${var.prefix}.${data.aws_route53_zone.zone.name}"
  type    = "CNAME"
  ttl     = "300"
  records = ["${kubernetes_service.quay_lb_service.status.0.load_balancer.0.ingress.0.hostname}"]
}

resource "aws_route53_record" "quay_hostname" {
  zone_id = data.aws_route53_zone.zone.zone_id
  name    = "${var.dns_domain}"
  type    = "CNAME"
  ttl     = "60"
  allow_overwrite = true
  records = ["${kubernetes_service.quay_lb_service.status.0.load_balancer.0.ingress.0.hostname}"]
}

