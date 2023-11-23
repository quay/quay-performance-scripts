module "quay_vpc" {
  source  = "terraform-aws-modules/vpc/aws"
  version = "5.1.2"

  name                 = "${var.prefix}-vpc"
  cidr                 = "${var.quay_vpc_cidr}"
  azs                  = data.aws_availability_zones.available.names
  public_subnets       = [cidrsubnet(var.quay_vpc_cidr, 8, 0), cidrsubnet(var.quay_vpc_cidr, 8, 1), cidrsubnet(var.quay_vpc_cidr, 8, 2)]
  enable_dns_hostnames = true
  enable_dns_support   = true
  create_elasticache_subnet_group	= true

  tags = {
    Environment = "${var.prefix}"
  }
}

data "http" "self_public_ip" {
  url = "http://ipv4.icanhazip.com"
}

data "aws_vpc" "openshift_vpc" {
  id = var.openshift_vpc_id
}

resource "aws_db_subnet_group" "db_subnet" {
  name       = "${var.prefix}-subnet"
  subnet_ids = module.quay_vpc.public_subnets

  tags = {
    Environment = "${var.prefix}"
  }

}

resource "aws_db_subnet_group" "db_subnet_group" {
  name       = "${var.prefix}-subnet-group"
  subnet_ids = module.quay_vpc.public_subnets

  tags = {
    Environment = "${var.prefix}"
  }
}

resource "aws_security_group" "db_security_group" {
  name   = "${var.prefix}-sg"
  vpc_id = module.quay_vpc.vpc_id

  # Mysql
  ingress {
    from_port   = 3306
    to_port     = 3306
    protocol    = "tcp"
    cidr_blocks = [data.aws_vpc.openshift_vpc.cidr_block, "${chomp(data.http.self_public_ip.response_body)}/32"]
  }

  egress {
    from_port   = 3306
    to_port     = 3306
    protocol    = "tcp"
    cidr_blocks = [data.aws_vpc.openshift_vpc.cidr_block, "${chomp(data.http.self_public_ip.response_body)}/32"]
  }

  # Postgres
  ingress {
    from_port   = 5432
    to_port     = 5432
    protocol    = "tcp"
    cidr_blocks = [data.aws_vpc.openshift_vpc.cidr_block, "${chomp(data.http.self_public_ip.response_body)}/32"]
  }

  egress {
    from_port   = 5432
    to_port     = 5432
    protocol    = "tcp"
    cidr_blocks = [data.aws_vpc.openshift_vpc.cidr_block, "${chomp(data.http.self_public_ip.response_body)}/32"]
  }

  # Redis
  ingress {
    from_port   = 6379
    to_port     = 6379
    protocol    = "tcp"
    cidr_blocks = [data.aws_vpc.openshift_vpc.cidr_block, "${chomp(data.http.self_public_ip.response_body)}/32"]
  }

  egress {
    from_port   = 6379
    to_port     = 6379
    protocol    = "tcp"
    cidr_blocks = [data.aws_vpc.openshift_vpc.cidr_block, "${chomp(data.http.self_public_ip.response_body)}/32"]
  }

  # Grpc
  ingress {
    from_port   = 55443
    to_port     = 55443
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  egress {
    from_port   = 55443
    to_port     = 55443
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  # ssh
  ingress {
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  egress {
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  # Internet
  ingress {
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  egress {
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  ingress {
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Environment = "${var.prefix}"
  }
}

resource "aws_vpc_peering_connection" "rds_openshift_peering" {
  peer_vpc_id   = data.aws_vpc.openshift_vpc.id
  vpc_id        = module.quay_vpc.vpc_id
  auto_accept   = true

  accepter {
    allow_remote_vpc_dns_resolution = true
  }

  requester {
    allow_remote_vpc_dns_resolution = true
  }

  tags = {
    Environment = "${var.prefix}"
  }
}


resource "aws_route_table" "rds_to_openshift_route_table" {
  vpc_id = module.quay_vpc.vpc_id

  tags = {
    Environment = "${var.prefix}"
  }
}

resource "aws_route" "rds_to_os_r" {
  route_table_id            = "${aws_route_table.rds_to_openshift_route_table.id}"
  destination_cidr_block    = "${data.aws_vpc.openshift_vpc.cidr_block}"
  vpc_peering_connection_id = "${aws_vpc_peering_connection.rds_openshift_peering.id}"
}

resource "aws_route" "os_to_rds_r" {
  route_table_id            = "${data.aws_vpc.openshift_vpc.main_route_table_id}"
  destination_cidr_block    = "${module.quay_vpc.vpc_cidr_block}"
  vpc_peering_connection_id = "${aws_vpc_peering_connection.rds_openshift_peering.id}"
}

/* TODO: Add route table entries to route ALB traffic to ELB 
resource "aws_route_table_association" "rds_to_os_assoc" {
    for_each = toset(module.quay_vpc.public_subnets)

    subnet_id = each.value
    route_table_id = aws_route_table.rds_to_openshift_route_table.id
} */

