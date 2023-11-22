
resource "aws_rds_cluster" "quay_db" {
  cluster_identifier      = "${var.prefix}-quay-db"
  engine                  = "aurora-postgresql"
  availability_zones      = ["us-east-1a", "us-east-1b", "us-east-1c"]
  database_name           = "quay"
  master_username         = "quay"
  master_password         = var.db_password
  apply_immediately       = true
  skip_final_snapshot     = true
  vpc_security_group_ids = [aws_security_group.db_security_group.id]
  db_subnet_group_name   = aws_db_subnet_group.db_subnet_group.name
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
  depends_on = [aws_rds_cluster_instance.quay_db_instance] # wait for the db to be ready
  provisioner "local-exec" {
    command = "PGPASSWORD=${var.db_password} psql -U ${aws_rds_cluster.quay_db.master_username} -h ${aws_rds_cluster.quay_db.endpoint} < setup-db.sql"
  }
}

