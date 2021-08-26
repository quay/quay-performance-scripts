resource "aws_s3_bucket" "quay_s3_storage" {
  bucket = "${var.prefix}-quay-storage"
  force_destroy = true

  versioning {
    enabled = true
  }

  tags = {
    Name        = "${var.prefix}-quay-storage"
    Environment = "perftest"
  }
}


locals {
  s3_origin_id = "${var.prefix}-origin-id"
}

resource "aws_cloudfront_distribution" "s3_distribution" {
  origin {
    domain_name = aws_s3_bucket.quay_s3_storage.bucket_regional_domain_name
    origin_id   = local.s3_origin_id
    origin_path = "/images"

    s3_origin_config {
      origin_access_identity = "${aws_cloudfront_origin_access_identity.quay_cloudfront_aoi.cloudfront_access_identity_path}"
    }
  }

  enabled             = true
  is_ipv6_enabled     = true
  default_root_object = "index.html"

  default_cache_behavior {
    allowed_methods  = ["DELETE", "GET", "HEAD", "OPTIONS", "PATCH", "POST", "PUT"]
    cached_methods   = ["GET", "HEAD"]
    target_origin_id = local.s3_origin_id

    forwarded_values {
      query_string = false

      cookies {
        forward = "none"
      }
    }

    viewer_protocol_policy = "allow-all"
    min_ttl                = 0
    default_ttl            = 3600
    max_ttl                = 86400
  }

  # Cache behavior with precedence 0
  ordered_cache_behavior {
    path_pattern     = "/*"
    allowed_methods  = ["GET", "HEAD", "OPTIONS"]
    cached_methods   = ["GET", "HEAD", "OPTIONS"]
    target_origin_id = local.s3_origin_id

    forwarded_values {
      query_string = false
      headers      = ["Origin"]

      cookies {
        forward = "none"
      }
    }

    min_ttl                = 0
    default_ttl            = 86400
    max_ttl                = 31536000
    compress               = true
    viewer_protocol_policy = "redirect-to-https"
    trusted_key_groups = [aws_cloudfront_key_group.quay_cloudfront_key_group.id]
  }

  price_class = "PriceClass_200"

  restrictions {
    geo_restriction {
      restriction_type = "whitelist"
      locations        = ["US", "CA", "GB", "DE"]
    }
  }

  tags = {
    Environment = "perftest"
  }

  viewer_certificate {
    cloudfront_default_certificate = true
  }
}

resource "aws_cloudfront_origin_access_identity" "quay_cloudfront_aoi" {}

resource "aws_s3_bucket_policy" "quay_cloudfront_acess" {
  bucket = "${aws_s3_bucket.quay_s3_storage.id}"
  policy = "${data.aws_iam_policy_document.quay_cloudfront_access.json}"
}

data "aws_iam_policy_document" "quay_cloudfront_access" {
  statement {
    actions   = ["s3:GetObject"]
    resources = ["${aws_s3_bucket.quay_s3_storage.arn}/*"]

    principals {
      type        = "AWS"
      identifiers = ["${aws_cloudfront_origin_access_identity.quay_cloudfront_aoi.iam_arn}"]
    }
  }

  statement {
    actions   = ["s3:ListBucket"]
    resources = ["${aws_s3_bucket.quay_s3_storage.arn}"]

    principals {
      type        = "AWS"
      identifiers = ["${aws_cloudfront_origin_access_identity.quay_cloudfront_aoi.iam_arn}"]
    }
  }
}


resource "aws_iam_user" "s3_user" {
  name = "${var.prefix}-s3-user"

  tags = {
    Environment = "${var.prefix}-env"
  }
}

resource "aws_iam_access_key" "s3_access_key" {
  user = aws_iam_user.s3_user.name
}

resource "aws_iam_user_policy" "s3_policy" {
  name = "${var.prefix}-s3-policy"
  user = aws_iam_user.s3_user.name

  policy = <<EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Action": [
        "s3:*",
        "cloudfront:*"
      ],
      "Effect": "Allow",
      "Resource": "*"
    }
  ]
}
EOF
}

resource "tls_private_key" "cloudfront_signing_private_key" {
  algorithm   = "RSA"
  rsa_bits = 2048
}

data "tls_public_key" "cloudfront_signing_public_key" {
  private_key_pem = tls_private_key.cloudfront_signing_private_key.private_key_pem
}

resource "aws_cloudfront_public_key" "quay_cloudfront_public_key" {
  comment     = "${var.prefix} Signing public key"
  encoded_key = data.tls_public_key.cloudfront_signing_public_key.public_key_pem
  name        = "${var.prefix}-signing-key"
}

resource "aws_cloudfront_key_group" "quay_cloudfront_key_group" {
  comment = "CF Key group for ${var.prefix}"
  items   = [aws_cloudfront_public_key.quay_cloudfront_public_key.id]
  name    = "${var.prefix}-signing-keygroup"
}
