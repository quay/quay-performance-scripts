module "rds_vpc" {
  source  = "terraform-aws-modules/vpc/aws"
  version = "2.77.0"

  name                 = "${var.prefix}-vpc"
  cidr                 = "${var.rds_vpc_cidr}"
  azs                  = data.aws_availability_zones.available.names
  public_subnets       = [cidrsubnet(var.rds_vpc_cidr, 8, 0), cidrsubnet(var.rds_vpc_cidr, 8, 1), cidrsubnet(var.rds_vpc_cidr, 8, 2)]
  enable_dns_hostnames = true
  enable_dns_support   = true
  create_elasticache_subnet_group	= true
}

data "aws_vpc" "openshift_vpc" {
  id = var.openshift_vpc_id
}

resource "aws_db_subnet_group" "db_subnet" {
  name       = "${var.prefix}-subnet"
  subnet_ids = module.rds_vpc.public_subnets

  tags = {
    Name = "${var.prefix}-subnet"
  }
}

resource "aws_db_subnet_group" "db_subnet_group" {
  name       = "${var.prefix}-subnet-group"
  subnet_ids = module.rds_vpc.public_subnets

  tags = {
    Name = "${var.prefix}-subnet-group"
  }
}

resource "aws_security_group" "db_security_group" {
  name   = "${var.prefix}-sg"
  vpc_id = module.rds_vpc.vpc_id

  # Mysql
  ingress {
    from_port   = 3306
    to_port     = 3306
    protocol    = "tcp"
    cidr_blocks = [data.aws_vpc.openshift_vpc.cidr_block]
  }

  egress {
    from_port   = 3306
    to_port     = 3306
    protocol    = "tcp"
    cidr_blocks = [data.aws_vpc.openshift_vpc.cidr_block]
  }

  # Postgres
  ingress {
    from_port   = 5432
    to_port     = 5432
    protocol    = "tcp"
    cidr_blocks = [data.aws_vpc.openshift_vpc.cidr_block]
  }

  egress {
    from_port   = 5432
    to_port     = 5432
    protocol    = "tcp"
    cidr_blocks = [data.aws_vpc.openshift_vpc.cidr_block]
  }

  # Redis
  ingress {
    from_port   = 6379
    to_port     = 6379
    protocol    = "tcp"
    cidr_blocks = [data.aws_vpc.openshift_vpc.cidr_block]
  }

  egress {
    from_port   = 6379
    to_port     = 6379
    protocol    = "tcp"
    cidr_blocks = [data.aws_vpc.openshift_vpc.cidr_block]
  }


  tags = {
    Name = "${var.prefix}-sg"
  }
}

resource "aws_vpc_peering_connection" "rds_openshift_peering" {
  peer_vpc_id   = data.aws_vpc.openshift_vpc.id
  vpc_id        = module.rds_vpc.vpc_id
  auto_accept   = true

  accepter {
    allow_remote_vpc_dns_resolution = true
  }

  requester {
    allow_remote_vpc_dns_resolution = true
  }

  tags = {
    Name = "${var.prefix}-rds-openshift-vpc-peering"
  }
}


resource "aws_route_table" "rds_to_openshift_route_table" {
  vpc_id = module.rds_vpc.vpc_id

  tags = {
    Name = "${var.prefix}-rds-to-openshift-rt"
  }
}

resource "aws_route" "rds_to_os_r" {
  route_table_id            = "${aws_route_table.rds_to_openshift_route_table.id}"
  destination_cidr_block    = "${data.aws_vpc.openshift_vpc.cidr_block}"
  vpc_peering_connection_id = "${aws_vpc_peering_connection.rds_openshift_peering.id}"
}

resource "aws_route" "os_to_rds_r" {
  route_table_id            = "${data.aws_vpc.openshift_vpc.main_route_table_id}"
  destination_cidr_block    = "${module.rds_vpc.vpc_cidr_block}"
  vpc_peering_connection_id = "${aws_vpc_peering_connection.rds_openshift_peering.id}"
}
