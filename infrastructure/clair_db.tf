resource "aws_db_instance" "clair_db" {
  identifier             = "${var.prefix}-clair-db"
  instance_class         = "db.t3.micro"
  allocated_storage      = 50
  engine                 = "postgres"
  engine_version         = "13.2"
  name                   = "clair"
  username               = "clair"
  password               = var.db_password
  db_subnet_group_name   = aws_db_subnet_group.db_subnet_group.name
  vpc_security_group_ids = [aws_security_group.db_security_group.id]
  parameter_group_name   = aws_db_parameter_group.clair_db_prameter_group.name
  publicly_accessible    = true
  skip_final_snapshot    = true
}

resource "aws_db_parameter_group" "clair_db_prameter_group" {
  name   = "${var.prefix}-clair-db-parameter-group"
  family = "postgres13"
}
