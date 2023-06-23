resource "aws_lb" "quay_alb" {
  name               = "${var.prefix}-alb"
  internal           = false
  load_balancer_type = "application"
  security_groups    = [aws_security_group.db_security_group.id]
  subnets            = module.quay_vpc.public_subnets

  enable_deletion_protection = false

  tags = {
    Environment = "${var.prefix}"
  }
}

resource "aws_lb_listener" "quay_http" {
  load_balancer_arn = "${aws_lb.quay_alb.arn}"
  port              = "80"
  protocol          = "HTTP"

  default_action {
    type = "redirect"

    redirect {
      port        = "443"
      protocol    = "HTTPS"
      status_code = "HTTP_301"
    }
  }
}

resource "aws_alb_listener" "quay_alb_https_listener" {
  load_balancer_arn = aws_lb.quay_alb.arn
  port              = "443"
  protocol          = "HTTPS"
  ssl_policy        = "ELBSecurityPolicy-2016-08"
  certificate_arn   = aws_acm_certificate.quay_domain_cert.arn

  default_action {
    type             = "forward"
    target_group_arn = aws_alb_target_group.quay_alb_https_target_group.arn
  }
}

resource "aws_alb_target_group" "quay_alb_https_target_group" {
  name     = "${var.prefix}-alb-https-tg"
  port     = "443"
  protocol = "HTTPS"
  target_type = "ip"
  vpc_id   = module.quay_vpc.vpc_id
}


resource "aws_alb_listener" "quay_alb_grpc_listener" {
  load_balancer_arn = aws_lb.quay_alb.arn
  port              = "55443"
  protocol          = "HTTPS"
  ssl_policy        = "ELBSecurityPolicy-2016-08"
  certificate_arn   = aws_acm_certificate.quay_domain_cert.arn

  default_action {
    type             = "forward"
    target_group_arn = aws_alb_target_group.quay_alb_grpc_target_group.arn
  }
}

resource "aws_alb_target_group" "quay_alb_grpc_target_group" {
  name     = "${var.prefix}-alb-grpcs-tg"
  port     = "55443"
  protocol = "HTTPS"
  target_type = "ip"
  vpc_id   = module.quay_vpc.vpc_id
  health_check {
     port = 443
  }
}

resource "aws_alb_listener" "quay_alb_metrics_listener" {
  load_balancer_arn = aws_lb.quay_alb.arn
  port              = "9091"
  protocol          = "HTTPS"
  ssl_policy        = "ELBSecurityPolicy-2016-08"
  certificate_arn   = aws_acm_certificate.quay_domain_cert.arn

  default_action {
    type             = "forward"
    target_group_arn = aws_alb_target_group.quay_alb_grpc_target_group.arn
  }
}

resource "aws_alb_target_group" "quay_alb_metrics_target_group" {
  name     = "${var.prefix}-alb-metrics-tg"
  port     = "9091"
  protocol = "HTTPS"
  target_type = "ip"
  vpc_id   = module.quay_vpc.vpc_id
  health_check {
     port = 443
  }
}

/* TODO: Add IPs of ELB automatically to the target group */
