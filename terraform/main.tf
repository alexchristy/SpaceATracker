provider "aws" {
	region = "us-east-1"
  
  default_tags {
    tags = {
      project = "spaceatracker"
      environment = "production"
      managedBy = "terraform" 
    }
  }
}

# Variables
# ----------
variable "db_password" {
	description 	= "Database administrator password"
	type		= string
	sensitive	= true
}

# Networking
# -----------
resource "aws_vpc" "main" {
	cidr_block = "10.0.0.0/16"
}
resource "aws_internet_gateway" "igw" {
	vpc_id = aws_vpc.main.id
}
resource "aws_subnet" "public_a" {
	vpc_id			= aws_vpc.main.id
	cidr_block		= "10.0.1.0/24"
	availability_zone	= "us-east-1a"
	map_public_ip_on_launch	= true
}
resource "aws_subnet" "public_b" {
	vpc_id			= aws_vpc.main.id
	cidr_block		= "10.0.2.0/24"
	availability_zone	= "us-east-1b"
	map_public_ip_on_launch	= true
}
resource "aws_route_table" "public" {
	vpc_id = aws_vpc.main.id
	route {
		cidr_block = "0.0.0.0/0"
		gateway_id = aws_internet_gateway.igw.id
	}
}
resource "aws_route_table_association" "subnet_a_public_route" {
	subnet_id	= aws_subnet.public_a.id
	route_table_id	= aws_route_table.public.id
}
resource "aws_route_table_association" "subnet_b_public_route" {
	subnet_id	= aws_subnet.public_b.id
	route_table_id	= aws_route_table.public.id
}

# Security groups
# ----------------
resource "aws_security_group" "main_vpc_allow_all_out" {
	vpc_id = aws_vpc.main.id

  ingress {
    from_port = 5432
    to_port   = 5432
    protocol  = "tcp"
    self      = true
  }
	egress {
		from_port 	= 0
		to_port		= 0
		protocol	= "-1"
		cidr_blocks 	= ["0.0.0.0/0"]
	}
}

# Database
# ---------
resource "aws_db_subnet_group" "db_subnet" {
	name		= "spaceatracker-db-subnet"
	subnet_ids	= [aws_subnet.public_a.id, aws_subnet.public_b.id]
}
resource "aws_db_instance" "postgres" {
	allocated_storage		= 20 
	engine			= "postgres"
	engine_version		= "18"
	instance_class		= "db.t4g.micro"
	username			= "spaceatracker"
	password		= var.db_password
	vpc_security_group_ids	= [aws_security_group.main_vpc_allow_all_out.id]
	db_subnet_group_name	= aws_db_subnet_group.db_subnet.name
	skip_final_snapshot	= true
}

# Container repositories
# -----------------------
resource "aws_ecr_repository" "worker_repo" {
	name = "spaceatracker"
}
resource "aws_ecr_repository" "migrate_repo" {
	name = "spaceatracker-migrate"
}
resource "aws_ecs_cluster" "cluster" {
	name = "spaceatracker-cluster"
}

# OIDC provider for Github Actions
# ---------------------------------
data "aws_iam_policy_document" "github_actions_trust" {
	statement {
		effect 	= "Allow"
		actions	= ["sts:AssumeRoleWithWebIdentity"]

		principals {
			type		= "Federated"
			identifiers	= [aws_iam_openid_connect_provider.github.arn]
		}

		condition {
			test		= "StringEquals"
			variable	= "token.actions.githubusercontent.com:aud"
			values		= ["sts.amazonaws.com"]
		}

		condition {
			test 		= "StringLike"
			variable	= "token.actions.githubusercontent.com:sub"
			values		= ["repo:alexchristy/SpaceATracker:*"]
		}
	}
}
resource "aws_iam_openid_connect_provider" "github" {
	url		= "https://token.actions.githubusercontent.com"
	client_id_list	= ["sts.amazonaws.com"]
	thumbprint_list	= ["1b511abead59c6ce207077c0bf0e0043b1382612"]
}
resource "aws_iam_role" "github_actions" {
	name = "GitHubActionsDeploymentRole"
	assume_role_policy = data.aws_iam_policy_document.github_actions_trust.json
}

# Output
# -------
output "rds_endpoint" {
	value = aws_db_instance.postgres.endpoint
}
