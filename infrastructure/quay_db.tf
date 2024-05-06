resource "aws_rds_global_cluster" "quay_global_db" {
  count = local.is_secondary ? 1 : 0
  force_destroy                = true
  global_cluster_identifier    = "${var.prefix}-global-quay-db"
  source_db_cluster_identifier = "${var.primary_db_arn}"
  database_name                = "quay"
}

resource "aws_rds_cluster" "quay_db" {
  cluster_identifier      = "${var.prefix}-quay-db"
  engine                  = "aurora-postgresql"
  availability_zones      = local.is_primary ? ["us-east-1a", "us-east-1b", "us-east-1c"] : ["us-east-2a", "us-east-2b", "us-east-2c"]
  database_name           = local.is_primary ? "quay" : null
  master_username         = local.is_primary ? "quay" : null
  master_password         = local.is_primary ? var.db_password : null
  apply_immediately       = true
  skip_final_snapshot     = true
  vpc_security_group_ids = [aws_security_group.db_security_group.id]
  db_subnet_group_name   = aws_db_subnet_group.db_subnet_group.name
  global_cluster_identifier = local.is_secondary ? aws_rds_global_cluster.quay_global_db[0].id : null
}

resource "aws_rds_cluster_instance" "quay_db_instance" {
  count              = 1
  identifier         = "${var.prefix}-quay-aurora-db"
  cluster_identifier = aws_rds_cluster.quay_db.id
  db_subnet_group_name   = aws_db_subnet_group.db_subnet_group.name
  instance_class     = "db.r6g.large"
  engine             = aws_rds_cluster.quay_db.engine
  engine_version     = aws_rds_cluster.quay_db.engine_version
  publicly_accessible = true
  apply_immediately       = true

}

resource "null_resource" "setup_db" {
  count = local.is_primary ? 1 : 0
  depends_on = [aws_rds_cluster_instance.quay_db_instance] # wait for the db to be ready
  provisioner "local-exec" {
    command = "PGPASSWORD=${var.db_password} psql -U ${aws_rds_cluster.quay_db.master_username} -h ${aws_rds_cluster.quay_db.endpoint} -c 'CREATE EXTENSION pg_trgm;'"
  }
}
