resource "aws_db_instance" "quay_db" {
  identifier             = "${var.prefix}-quay-db"
  instance_class         = "db.t3.micro"
  allocated_storage      = 5
  engine                 = "mysql"
  engine_version         = "5.7.41"
  name                   = "quay"
  username               = "quay"
  password               = var.db_password
  db_subnet_group_name   = aws_db_subnet_group.db_subnet_group.name
  vpc_security_group_ids = [aws_security_group.db_security_group.id]
  parameter_group_name   = aws_db_parameter_group.quay_db_prameter_group.name
  publicly_accessible    = true
  skip_final_snapshot    = true
  auto_minor_version_upgrade = false
  multi_az = var.quay_db_multi_az
  tags = {
    Deployment = "${var.prefix}"
  }

  replicate_source_db = var.deploy_type == "secondary" ? var.primary_db_arn : null
  backup_retention_period = 5
}

resource "aws_db_parameter_group" "quay_db_prameter_group" {
  name   = "${var.prefix}-quay-db-parameter-group"
  family = "mysql5.7"

  tags = {
    Deployment = "${var.prefix}"
  }
}
