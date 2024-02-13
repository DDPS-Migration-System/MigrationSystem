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
