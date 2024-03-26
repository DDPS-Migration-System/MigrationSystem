resource "aws_dynamodb_table" "stablespot_table" {
  name         = "${var.prefix}DynamoDB"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "InstanceId"
  range_key    = "InstanceName"

  attribute {
    name = "InstanceId"
    type = "S"
  }

  attribute {
    name = "InstanceName"
    type = "S"
  }

  tags = {
    Name = "${var.prefix}DynamoDBTable"
  }
}
