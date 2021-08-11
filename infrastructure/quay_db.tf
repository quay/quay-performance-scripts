resource "aws_db_instance" "quay_db" {
  identifier             = "${var.prefix}-quay-db"
  instance_class         = "db.t3.micro"
  allocated_storage      = 5
  engine                 = "mysql"
  engine_version         = "5.7.33"
  name                   = "quay"
  username               = "quay"
  password               = var.db_password
  db_subnet_group_name   = aws_db_subnet_group.db_subnet_group.name
  vpc_security_group_ids = [aws_security_group.db_security_group.id]
  parameter_group_name   = aws_db_parameter_group.quay_db_prameter_group.name
  publicly_accessible    = true
  skip_final_snapshot    = true
  auto_minor_version_upgrade = false
}

resource "aws_db_parameter_group" "quay_db_prameter_group" {
  name   = "${var.prefix}-quay-db-parameter-group"
  family = "mysql5.7"
}
