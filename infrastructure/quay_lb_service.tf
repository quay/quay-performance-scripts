resource "kubernetes_service" "quay_lb_service" {
  metadata {
    name = "${var.prefix}-quay-lb"
    namespace = "${kubernetes_namespace.quay_ns.metadata[0].name}"
  }

  spec {
    selector = {
      "quay-component" = "quay-app"
    }
    port {
      name        = "https"
      port        = 443
      target_port = 8443
    }
    port {
      name        = "http"
      port        = 80
      target_port = 8080
    }
    port {
      name        = "jwtproxy"
      port        = 8081
      target_port = 8081
    }
    port {
      name        = "grpc"
      port        = 55443
      target_port = 55443
    }
    port {
      name        = "metrics"
      port        = 9091
      target_port = 9091
    }

    type = "LoadBalancer"
  }
}
