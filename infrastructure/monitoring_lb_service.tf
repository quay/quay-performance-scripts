resource "kubernetes_service" "prometheus_lb_service" {
  count = var.enable_monitoring ? 1 : 0
  metadata {
    name = "${var.prefix}-prometheus-lb"
    namespace = "${kubernetes_namespace.quay_ns.metadata[0].name}"
  }

  spec {
    selector = {
      "app" = "prometheus-app"
    }
    port {
      name        = "prometheus"
      port        = 9090
      target_port = 9090
    }
    type = "LoadBalancer"
  }
}

resource "kubernetes_service" "grafana_lb_service" {
  count = var.enable_monitoring ? 1 : 0
  metadata {
    name = "${var.prefix}-grafana-lb"
    namespace = "${kubernetes_namespace.quay_ns.metadata[0].name}"
  }
  spec {
    selector = {
      "app" = "grafana-app"
    }
    port {
      name        = "grafana-http"
      port        = 80
      target_port = 3000
    }
    port {
      name        = "grafana-https"
      port        = 443
      target_port = 3000
    }
    type = "LoadBalancer"
  }

}
