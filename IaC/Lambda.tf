resource "aws_lambda_function" "stablespot_create_spot" {
  function_name = "stablespot-create-spot"
  handler       = "lambda_function.lambda_handler" # 가정: Lambda 함수의 핸들러는 index 파일의 handler 메서드
  runtime       = "python3.10"
  role          = aws_iam_role.lambda_exec_role.arn
  filename      = "${path.module}/stablespot-create-spot.zip"

  source_code_hash = filebase64sha256("${path.module}/stablespot-create-spot.zip")

  tags = {
    Name = "${var.prefix}-create-spot"
  }
}

resource "aws_lambda_function" "stablespot_migration_by_interrupt" {
  function_name = "stablespot-migration-by-interrupt"
  handler       = "lambda_function.lambda_handler"
  runtime       = "python3.10"
  role          = aws_iam_role.lambda_exec_role.arn
  filename      = "${path.module}/stablespot-migration-by-interrupt.zip"

  source_code_hash = filebase64sha256("${path.module}/stablespot-migration-by-interrupt.zip")

  tags = {
    Name = "${var.prefix}-migration-by-interrupt"
  }
}

resource "aws_lambda_function" "stablespot_paginator" {
  function_name = "stablespot-paginator"
  handler       = "lambda_function.lambda_handler"
  runtime       = "python3.10"
  role          = aws_iam_role.lambda_exec_role.arn
  filename      = "${path.module}/stablespot-paginator.zip"

  source_code_hash = filebase64sha256("${path.module}/stablespot-paginator.zip")

  tags = {
    Name = "${var.prefix}-paginator"
  }
}

resource "aws_lambda_function" "stablespot_controller" {
  function_name = "stablespot-controller"
  handler       = "lambda_function.lambda_handler"
  runtime       = "python3.10"
  role          = aws_iam_role.lambda_exec_role.arn
  filename      = "${path.module}/stablespot-controller.zip"

  source_code_hash = filebase64sha256("${path.module}/stablespot-controller.zip")

  tags = {
    Name = "${var.prefix}-controller"
  }
}

resource "aws_lambda_function" "stablespot_registor" {
  function_name = "stablespot-registor"
  handler       = "lambda_function.lambda_handler"
  runtime       = "python3.10"
  role          = aws_iam_role.lambda_exec_role.arn
  filename      = "${path.module}/stablespot-registor.zip"

  source_code_hash = filebase64sha256("${path.module}/stablespot-registor.zip")

  tags = {
    Name = "${var.prefix}-registor"
  }
}

resource "aws_iam_role" "lambda_exec_role" {
  name = "${var.prefix}-lambda-exec-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17",
    Statement = [
      {
        Action = "sts:AssumeRole",
        Effect = "Allow",
        Principal = {
          Service = "lambda.amazonaws.com"
        }
      },
    ]
  })

  # IAM 정책을 추가하여 필요한 권한을 할당합니다.
}

resource "aws_lambda_function_url" "stablespot_create_spot_url" {
  function_name = aws_lambda_function.stablespot_create_spot.function_name
  qualifier     = "$LATEST"

  authorization_type = "NONE" # 'NONE', 'AWS_IAM' 또는 'JWT' 중에서 선택

  # 'JWT'를 사용하는 경우 아래와 같이 설정할 수 있습니다.
  # cors {
  #   allow_credentials = false
  #   allow_headers     = ["*"]
  #   allow_methods     = ["POST"]
  #   allow_origins     = ["https://example.com"]
  #   expose_headers    = []
  #   max_age           = 3600
  # }
}

resource "aws_lambda_function_url" "stablespot_migration_by_interrupt_url" {
  function_name = aws_lambda_function.stablespot_migration_by_interrupt.function_name
  qualifier     = "$LATEST"

  authorization_type = "NONE"
}

resource "aws_lambda_function_url" "stablespot_paginator_url" {
  function_name = aws_lambda_function.stablespot_paginator.function_name
  qualifier     = "$LATEST"

  authorization_type = "NONE"
}

resource "aws_lambda_function_url" "stablespot_controller_url" {
  function_name = aws_lambda_function.stablespot_controller.function_name
  qualifier     = "$LATEST"

  authorization_type = "NONE"
}

resource "aws_lambda_function_url" "stablespot_registor_url" {
  function_name = aws_lambda_function.stablespot_registor.function_name
  qualifier     = "$LATEST"

  authorization_type = "NONE"
}

output "stablespot_create_spot_function_url" {
  value = aws_lambda_function_url.stablespot_create_spot_url.function_url
}

output "stablespot_migration_by_interrupt_function_url" {
  value = aws_lambda_function_url.stablespot_migration_by_interrupt_url.function_url
}

output "stablespot_paginator_function_url" {
  value = aws_lambda_function_url.stablespot_paginator_url.function_url
}

output "stablespot_controller_function_url" {
  value = aws_lambda_function_url.stablespot_controller_url.function_url
}

output "stablespot_registor_function_url" {
  value = aws_lambda_function_url.stablespot_registor_url.function_url
}
