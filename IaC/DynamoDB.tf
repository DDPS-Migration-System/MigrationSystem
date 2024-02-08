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

  tags = {
    Name = "${var.prefix}DynamoDBTable"
  }
}
