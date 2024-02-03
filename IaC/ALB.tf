resource "aws_lb" "stablespot_alb" {
  name               = "${var.prefix}-alb"
  internal           = false
  load_balancer_type = "application"
  security_groups    = [aws_security_group.alb_sg.id]
  subnets            = [aws_subnet.stablespot_public_subnet[*].id]

  enable_deletion_protection = false

  tags = {
    Name = "${var.prefix}-alb"
  }
}

resource "aws_security_group" "alb_sg" {
  name        = "${var.prefix}-alb-sg"
  description = "Security group for the ALB"
  vpc_id      = aws_vpc.stablespot_vpc.id

  ingress {
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"] # 전체 인터넷에서 HTTPS 트래픽을 허용
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"] # 모든 아웃바운드 트래픽 허용
  }
}


resource "aws_lb_listener" "https_listener" {
  load_balancer_arn = aws_lb.stablespot_alb.arn
  port              = "443"
  protocol          = "HTTPS"
  ssl_policy        = "ELBSecurityPolicy-TLS13-1-2-2021-06"

  certificate_arn   = aws_acm_certificate.acm.arn

  default_action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.stablespot_tg.arn
  }
}

resource "aws_lb_target_group" "stablespot_tg" {
  name     = "${var.prefix}-tg"
  port     = 80
  protocol = "HTTP"
  vpc_id   = aws_vpc.stablespot_vpc.id

  health_check {
    enabled             = true
    interval            = 30
    path                = "/"
    protocol            = "HTTP"
    timeout             = 5
    healthy_threshold   = 2
    unhealthy_threshold = 2
  }
}

# HTTPS 리스너에 대한 추가 경로 기반 라우팅 규칙 (필요한 경우)
resource "aws_lb_listener_rule" "jwt_authentication" {
  listener_arn = aws_lb_listener.https_listener.arn
  priority     = 100

  action {
    type = "authenticate-cognito"
    authenticate_cognito {
      user_pool_arn       = aws_cognito_user_pool.stablespot_user_pool.arn
      user_pool_client_id = aws_cognito_user_pool_client.stablespot_user_pool_client.id
      user_pool_domain    = aws_cognito_user_pool_domain.stablespot_domain.domain
    }
  }

  action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.server_group.arn
  }

  condition {
    path_pattern {
      values = ["/server"]
    }
  }
}

resource "aws_lb_target_group" "server_group" {
  name     = "${var.prefix}-server-group"
  port     = 80
  protocol = "HTTP"
  vpc_id   = aws_vpc.stablespot_vpc.id

  health_check {
    enabled     = true
    interval    = 30
    path        = "/"
    protocol    = "HTTP"
    timeout     = 5
    healthy_threshold   = 2
    unhealthy_threshold = 2
  }
}

resource "aws_lb_target_group_attachment" "server_instance" {
  target_group_arn = aws_lb_target_group.server_group.arn
  target_id        = "1.2.3.4"
  port             = 80
}
