provider "aws" {
  alias  = "east1"
  region = "us-east-1"
}

resource "aws_s3_bucket" "quay_s3_storage" {
  bucket = "${var.prefix}-quay-storage"
  force_destroy = true
  tags = {
    Name        = "${var.prefix}-quay-storage"
    Environment = "perftest"
  }
}

resource "aws_s3_bucket_versioning" "quay_s3_storage" {
  bucket = aws_s3_bucket.quay_s3_storage.id
  versioning_configuration {
    status = "Enabled"
  }
  depends_on = [aws_s3_bucket.quay_s3_storage]
}

resource "aws_s3_bucket_cors_configuration" "quay_s3_cors" {
  bucket = aws_s3_bucket.quay_s3_storage.id
  cors_rule {
     allowed_headers = ["*"]
     allowed_methods = ["PUT","POST", "GET", "DELETE"]
     allowed_origins = ["*"]
     expose_headers = ["ETag"]
     max_age_seconds = 3000
  }
}

resource "aws_iam_role" "replication" {
  name = "${var.prefix}-iam-role-replication"
  count = local.is_secondary ? 1 : 0
  assume_role_policy = <<POLICY
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Action": "sts:AssumeRole",
      "Principal": {
        "Service": "s3.amazonaws.com"
      },
      "Effect": "Allow",
      "Sid": ""
    }
  ]
}
POLICY
}

resource "aws_iam_policy" "replication" {
  name = "${var.prefix}-iam-role-policy-replication"
  count = local.is_secondary ? 1 : 0
  policy = <<POLICY
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Action": [
        "s3:GetReplicationConfiguration",
        "s3:ListBucket"
      ],
      "Effect": "Allow",
      "Resource": [
        "${var.primary_s3_bucket_arn}"
      ]
    },
    {
      "Action": [
        "s3:GetObjectVersionForReplication",
        "s3:GetObjectVersionAcl",
         "s3:GetObjectVersionTagging"
      ],
      "Effect": "Allow",
      "Resource": [
        "${var.primary_s3_bucket_arn}/*"
      ]
    },
    {
      "Action": [
        "s3:ReplicateObject",
        "s3:ReplicateDelete",
        "s3:ReplicateTags"
      ],
      "Effect": "Allow",
      "Resource": "${aws_s3_bucket.quay_s3_storage.arn}/*"
    }
  ]
}
POLICY
}

resource "aws_iam_role_policy_attachment" "replication" {
  role       = aws_iam_role.replication[0].name
  policy_arn = aws_iam_policy.replication[0].arn
  count = local.is_secondary ? 1 : 0
}

resource "aws_s3_bucket_replication_configuration" "quay_s3_storage_replication" {
  provider = aws.east1
  count = local.is_secondary ? 1 : 0
  depends_on = [aws_s3_bucket_versioning.quay_s3_storage]

  role   = aws_iam_role.replication[0].arn
  bucket =  reverse(split(":", var.primary_s3_bucket_arn))[0] # Gets bucket name from ARN

  rule {
    id = "quay-replication-to-secondary"

    status = "Enabled"

    destination {
      bucket = aws_s3_bucket.quay_s3_storage.arn
    }
  }
}
