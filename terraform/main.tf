# Purpose: EC2 instance, default VPC networking, and security group for the
# Hangman deployment. IAM is in iam.tf, the budget alert is in budget.tf.
#
# Design: the instance is launched directly into the default VPC's default
# subnet for the chosen region - no custom VPC, since this is a short-lived
# grading deployment and the default VPC's subnets are already public
# (map_public_ip_on_launch = true). No Elastic IP: the auto-assigned public
# IP is fine for a deployment that only needs to survive until grading and
# will be destroyed afterward (see terraform/README.md).

terraform {
  required_version = ">= 1.5"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

# The provider region doubles as the Bedrock "source region" (config.py's
# BEDROCK_REGION) - the EC2 instance calls Bedrock from the same region it
# runs in, matching how this was tested locally.
provider "aws" {
  region = var.bedrock_region
}

data "aws_caller_identity" "current" {}

data "aws_vpc" "default" {
  default = true
}

data "aws_subnets" "default" {
  filter {
    name   = "vpc-id"
    values = [data.aws_vpc.default.id]
  }
}

# Amazon Linux 2023: current AWS-maintained image, dnf-based, systemd by
# default, and python3 ships with the venv module built in (no separate
# python3-venv package to remember, unlike Debian/Ubuntu). Looked up by
# name instead of a hardcoded AMI ID so it doesn't go stale.
#
# The name filter is anchored on "al2023-ami-2023." (not just "al2023-ami-*")
# so it only matches the standard AMI - a bare wildcard would also match the
# "al2023-ami-minimal-..." and "al2023-ami-ecs-hvm-..." variants, and
# most_recent could then silently pick one of those instead.
data "aws_ami" "al2023" {
  most_recent = true
  owners      = ["amazon"]

  filter {
    name   = "name"
    values = ["al2023-ami-2023.*-x86_64"]
  }

  filter {
    name   = "architecture"
    values = ["x86_64"]
  }

  filter {
    name   = "virtualization-type"
    values = ["hvm"]
  }
}

resource "aws_security_group" "hangman" {
  name        = "hangman-web"
  description = "Hangman web server: HTTP from anywhere, SSH from my_ip_cidr only"
  vpc_id      = data.aws_vpc.default.id

  ingress {
    description = "HTTP"
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  ingress {
    description = "SSH (restricted to my_ip_cidr)"
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = [var.my_ip_cidr]
  }

  egress {
    description = "All outbound"
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name = "hangman-web"
  }
}

resource "aws_instance" "hangman" {
  ami                         = data.aws_ami.al2023.id
  instance_type               = var.instance_type
  subnet_id                   = tolist(data.aws_subnets.default.ids)[0]
  vpc_security_group_ids      = [aws_security_group.hangman.id]
  iam_instance_profile        = aws_iam_instance_profile.hangman.name
  key_name                    = var.key_name
  associate_public_ip_address = true

  user_data = templatefile("${path.module}/user_data.sh.tftpl", {
    bedrock_region   = var.bedrock_region
    bedrock_model_id = var.bedrock_model_id
  })

  tags = {
    Name = "hangman-web"
  }
}
