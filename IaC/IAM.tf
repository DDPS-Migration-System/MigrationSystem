resource "aws_iam_role" "spot-instance-role" {
  name = "${var.prefix}-spot-instance-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "ec2.amazonaws.com"
        }
      }
    ]
  })
}

resource "aws_iam_instance_profile" "spot-instance-profile" {
  name = "${var.prefix}-spot-instance-profile"
  role = aws_iam_role.spot-instance-role.name
}
