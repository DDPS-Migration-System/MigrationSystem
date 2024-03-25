resource "aws_ssm_parameter" "creater_url" {
  name = "${var.prefix}-create-server"
  type = "String"
  value = aws_lambda_function_url.stablespot_create_spot_url.function_url
}

resource "aws_ssm_parameter" "paginator_url" {
  name = "${var.prefix}-get-server-list"
  type = "String"
  value = aws_lambda_function_url.stablespot_paginator_url.function_url
}

resource "aws_ssm_parameter" "controller_url" {
  name = "${var.prefix}-instance-controller"
  type = "String"
  value = aws_lambda_function_url.stablespot_controller_url.function_url
}

resource "aws_ssm_parameter" "registor_url" {
  name = "${var.prefix}-create-user"
  type = "String"
  value = aws_lambda_function_url.stablespot_registor_url.function_url
}

resource "aws_ssm_parameter" "efs_id" {
  name = "${var.prefix}-efs-id"
  type = "String"
  value = aws_efs_file_system.efs.id
}

resource "aws_ssm_parameter" "cognito_user_pool_id" {
  name = "${var.prefix}-user-pool-id"
  type = "String"
  value = aws_cognito_user_pool.stablespot_user_pool.id
}

resource "aws_ssm_parameter" "cognito_user_pool_client_id" {
  name = "${var.prefix}-user-pool-client-id"
  type = "String"
  value = aws_cognito_user_pool_client.stablespot_user_pool_client.id
}

resource "aws_ssm_parameter" "congito_user_pool_keys_url" {
  name = "${var.prefix}-user-pool-keys-url"
  type = "String"
  value = "https://cognito-idp.${var.region}.amazonaws.com/${aws_cognito_user_pool.stablespot_user_pool.id}/.well-known/jwks.json"
}

resource "aws_ssm_parameter" "cognito_user_pool_client_secret" {
  name = "${var.prefix}-user-pool-client-secret"
  type = "String"
  value = aws_cognito_user_pool_client.stablespot_user_pool_client.client_secret
}
