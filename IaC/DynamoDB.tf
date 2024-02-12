resource "aws_dynamodb_table" "example_table" {
  name         = "${var.prefix}DynamoDB"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "InstanceId"

  attribute {
    name = "InstanceId"
    type = "S"
  }

  attribute {
    name = "InstanceName"
    type = "S"
  }

  attribute {
    name = "InstanceType"
    type = "S"
  }

  attribute {
    name = "AvailabilityZone"
    type = "S"
  }

  attribute {
    name = "Status"
    type = "S"
  }

  attribute {
    name = "UserName"
    type = "S"
  }

  attribute {
    name = "UserData"
    type = "S"
  }

  attribute {
    name = "SupportSSH"
    type = "S"
  }

  attribute {
    name = "SupportWebService"
    type = "S"
  }

  tags = {
    Name = "${var.prefix}DynamoDBTable"
  }
}
