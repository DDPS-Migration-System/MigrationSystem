resource "aws_cognito_user_pool" "stablespot_user_pool" {
  name = "${var.prefix}-user-pool"

  password_policy {
    minimum_length    = 8
    require_lowercase = true
    require_numbers   = true
    require_symbols   = true
    require_uppercase = true
  }

  schema {
    attribute_data_type      = "String"
    name                     = "email"
    required                 = true
    string_attribute_constraints {
      min_length            = 7
      max_length            = 256
    }
  }

  auto_verified_attributes = ["email"]

  tags = {
    Name = "${var.prefix}-user-pool"
  }
}

resource "aws_cognito_user_pool_client" "stablespot_user_pool_client" {
  name         = "${var.prefix}-user-pool-client"
  user_pool_id = aws_cognito_user_pool.stablespot_user_pool.id

  explicit_auth_flows = [
    "ADMIN_NO_SRP_AUTH",
    "CUSTOM_AUTH_FLOW_ONLY",
    "USER_PASSWORD_AUTH"
  ]

  generate_secret = true

  callback_urls = ["https://your-callback-url.com"]
  logout_urls   = ["https://your-logout-url.com"]

  allowed_oauth_flows = [
    "code",
    "implicit"
  ]

  allowed_oauth_scopes = [
    "email",
    "openid",
    "profile"
  ]

  allowed_oauth_flows_user_pool_client = true
}

resource "aws_cognito_user_pool_domain" "stablespot_domain" {
  domain       = "${var.prefix}-cog-domain"
  user_pool_id = aws_cognito_user_pool.stablespot_user_pool.id
}

# Cognito 사용자 풀 ARN 출력
output "user_pool_arn" {
  value = aws_cognito_user_pool.stablespot_user_pool.arn
}

# Cognito 사용자 풀 클라이언트 ID 출력
output "user_pool_client_id" {
  value = aws_cognito_user_pool_client.stablespot_user_pool_client.id
}

# Cognito 도메인 출력 (도메인 리소스가 정의된 경우)
output "user_pool_domain" {
  value = aws_cognito_user_pool_domain.stablespot_domain.domain
}
