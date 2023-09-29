locals {
  is_secondary = "${var.deploy_type}" == "secondary" ? 1 : 0
}

provider "aws" {
  alias = "primary"
  region = "us-east-1"
}

resource "aws_s3_bucket" "quay_s3_storage" {
  bucket = "${var.prefix}-quay-storage"
  force_destroy = true
  versioning {
    enabled = true
  }

  cors_rule {
     allowed_headers = ["*"]
     allowed_methods = ["PUT","POST", "GET", "DELETE"]
     allowed_origins = ["*"]
     expose_headers = ["ETag"]
     max_age_seconds = 3000
  }

  tags = {
    Name        = "${var.prefix}-quay-storage"
    Environment = "perftest"
  }
}

data "aws_iam_policy_document" "assume_role" {
  statement {
    effect = "Allow"

    principals {
      type = "Service"
      identifiers = ["s3.amazonaws.com"]
    }

    actions = ["sts:AssumeRole"]
  }
}

resource "aws_iam_role" "replication" {
  name = "${var.prefix}-iam-role-replication"
  count = local.is_secondary
  assume_role_policy = data.aws_iam_policy_document.assume_role.json
}

data "aws_iam_policy_document" "replication" {
  statement {
    effect = "Allow"

    actions = [
      "s3:GetReplicationConfiguration",
      "s3:ListBucket",
    ]

    resources = ["${var.primary_s3_bucket_arn}"]
  }

  statement {
    effect = "Allow"

    actions = [
      "s3:GetObjectVersionForReplication",
      "s3:GetObjectVersionAcl",
      "s3:GetObjectVersionTagging"
    ]

    resources = ["${var.primary_s3_bucket_arn}/*"]
  }
  statement {
    effect = "Allow"

    actions = [
      "s3:ReplicateObject",
      "s3:ReplicateDelete",
      "s3:ReplicateTags"
    ]

    resources = ["${aws_s3_bucket.quay_s3_storage.arn}/*"]
  }
}

resource "aws_iam_policy" "replication" {
  name = "${var.prefix}-iam-role-policy-replication"
  count = local.is_secondary
  policy = data.aws_iam_policy_document.replication.json
}

resource "aws_iam_role_policy_attachment" "replication" {
  role       = aws_iam_role.replication[0].name
  policy_arn = aws_iam_policy.replication[0].arn
  count = local.is_secondary
} 

resource "aws_s3_bucket_replication_configuration" "replication" {
  provider = aws.primary
  count = local.is_secondary
  role = aws_iam_role.replication[0].arn
  bucket = var.primary_s3_bucket_name

  rule {
    id = "quay-replication"
    status = "Enabled"
    destination {
      bucket = aws_s3_bucket.quay_s3_storage.arn
      storage_class = "STANDARD"
    }
  }
}
