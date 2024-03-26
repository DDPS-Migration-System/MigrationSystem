resource "aws_s3_bucket" "stablespot_website" {
  bucket = "${var.prefix}-website"

  tags = {
    Name = "${var.prefix}-website"
  }
}

resource "aws_s3_bucket_public_access_block" "stablespot_website_public_access_block" {
  bucket = aws_s3_bucket.stablespot_website.id

  block_public_acls   = false
  ignore_public_acls  = false
  block_public_policy = false
  restrict_public_buckets = false
}

resource "aws_s3_bucket_ownership_controls" "stablespot_website_ownership_control" {
  bucket = aws_s3_bucket.stablespot_website.id

  rule {
    object_ownership = "BucketOwnerPreferred"
  }

  depends_on = [ aws_s3_bucket_public_access_block.stablespot_website_public_access_block ]
}

resource "aws_s3_bucket_policy" "website_bucket_policy" {
  bucket = aws_s3_bucket.stablespot_website.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action    = ["s3:GetObject"]
        Effect    = "Allow"
        Resource  = ["${aws_s3_bucket.stablespot_website.arn}/*"]
        Principal = "*"
      },
    ]
  })

  depends_on = [ aws_s3_bucket_public_access_block.stablespot_website_public_access_block ]
}

resource "aws_s3_bucket_acl" "stablespot_website_acl" {
  bucket = aws_s3_bucket.stablespot_website.bucket
  acl    = "public-read"

  depends_on = [ aws_s3_bucket_ownership_controls.stablespot_website_ownership_control ]
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
