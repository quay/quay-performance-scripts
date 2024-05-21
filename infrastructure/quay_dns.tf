
data "aws_route53_zone" "zone" {
  name         = "${var.dns_zone}"
  private_zone = false
}

resource "aws_route53_record" "quay" {
  zone_id = data.aws_route53_zone.zone.zone_id
  name    = "${var.prefix}.${data.aws_route53_zone.zone.name}"
  type    = "CNAME"
  ttl     = "60"
  allow_overwrite = true
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

resource "aws_route53_record" "prometheus_hostname" {
  count = var.enable_monitoring ? 1 : 0
  zone_id = data.aws_route53_zone.zone.zone_id
  name = "prometheus-${var.prefix}.${data.aws_route53_zone.zone.name}"
  type = "CNAME"
  ttl = "60"
  records = ["${kubernetes_service.prometheus_lb_service[0].status.0.load_balancer.0.ingress.0.hostname}"]
}

resource "aws_route53_record" "grafana_hostname" {
  count = var.enable_monitoring ? 1 : 0
  zone_id = data.aws_route53_zone.zone.zone_id
  name = "grafana-${var.prefix}.${data.aws_route53_zone.zone.name}"
  type = "CNAME"
  ttl = "60"
  records = ["${kubernetes_service.grafana_lb_service[0].status.0.load_balancer.0.ingress.0.hostname}"]
}

