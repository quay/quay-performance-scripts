locals {
  is_secondary = var.deploy_type == "secondary" ? 1 : 0
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

resource "aws_iam_role" "replication" {
  name = "${var.prefix}-iam-role-replication"
  count = local.is_secondary
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
  count = local.is_secondary
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
  count = local.is_secondary
} 
