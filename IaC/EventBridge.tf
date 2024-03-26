resource "aws_cloudwatch_event_rule" "spot_interruption" {
  name        = "${var.prefix}-spot-interruption"
  description = "Capture Spot Instance Interruptions"

  event_pattern = jsonencode({
    "source" : ["aws.ec2"],
    "detail-type" : ["EC2 Spot Instance Interruption Warning"]
  })
}

resource "aws_cloudwatch_event_target" "interrupt_lambda" {
  rule      = aws_cloudwatch_event_rule.spot_interruption.name
  target_id = "InterruptLambdaFunction"
  arn       = aws_lambda_function.stablespot_migration_by_interrupt.arn
}

# CPU, Memory Usage 알람은 구조상의 문제로 Terraform이 아닌 추후 Lambda에서 스팟 인스턴스를 생성할 때 같이 생성되도록 구성
