resource "aws_s3_bucket" "stablespot_website" {
  bucket = "${var.prefix}-website"

  tags = {
    Name = "${var.prefix}-website"
  }
}

resource "aws_s3_bucket_acl" "stablespot_website_acl" {
  bucket = aws_s3_bucket.stablespot_website.bucket
  acl    = "public-read"
}

resource "aws_s3_bucket_website_configuration" "stablespot_website_config" {
  bucket = aws_s3_bucket.stablespot_website.bucket

  index_document {
    suffix = "index.html"
  }

  error_document {
    key = "error.html"
  }
}

locals {
  web_files = fileset("${path.module}/s3_web/", "**/*")
}

resource "aws_s3_object" "example_file" {
  for_each = { for f in local.web_files : f => f }

  bucket = aws_s3_bucket.stablespot_website.bucket
  key    = each.value
  source = "${path.module}/s3_web/${each.value}"
  etag   = filemd5("${path.module}/s3_web/${each.value}")
}
