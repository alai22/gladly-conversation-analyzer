# Terraform configuration for Gladly Conversation Analyzer
terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
  
  required_version = ">= 1.0"
}

provider "aws" {
  region = var.aws_region
}

# Variables
variable "aws_region" {
  description = "AWS region"
  type        = string
  default     = "us-east-1"
}

variable "environment" {
  description = "Environment name"
  type        = string
  default     = "gladly-prod"
}

variable "instance_type" {
  description = "EC2 instance type"
  type        = string
  default     = "t3.medium"
}

variable "github_repository" {
  description = "GitHub repository URL"
  type        = string
  default     = "https://github.com/YOUR_USERNAME/gladly-conversation-analyzer"
}

# Data sources
data "aws_availability_zones" "available" {
  state = "available"
}

data "aws_caller_identity" "current" {}

# VPC Configuration
resource "aws_vpc" "gladly_vpc" {
  cidr_block           = "10.0.0.0/16"
  enable_dns_hostnames = true
  enable_dns_support   = true

  tags = {
    Name        = "${var.environment}-vpc"
    Environment = var.environment
  }
}

resource "aws_subnet" "public_subnet" {
  vpc_id                  = aws_vpc.gladly_vpc.id
  cidr_block              = "10.0.1.0/24"
  availability_zone       = data.aws_availability_zones.available.names[0]
  map_public_ip_on_launch = true

  tags = {
    Name        = "${var.environment}-public-subnet"
    Environment = var.environment
  }
}

resource "aws_internet_gateway" "gladly_igw" {
  vpc_id = aws_vpc.gladly_vpc.id

  tags = {
    Name        = "${var.environment}-igw"
    Environment = var.environment
  }
}

resource "aws_route_table" "public_rt" {
  vpc_id = aws_vpc.gladly_vpc.id

  route {
    cidr_block = "0.0.0.0/0"
    gateway_id = aws_internet_gateway.gladly_igw.id
  }

  tags = {
    Name        = "${var.environment}-public-rt"
    Environment = var.environment
  }
}

resource "aws_route_table_association" "public_rta" {
  subnet_id      = aws_subnet.public_subnet.id
  route_table_id = aws_route_table.public_rt.id
}

# Security Groups
resource "aws_security_group" "gladly_sg" {
  name_prefix = "gladly-${var.environment}-"
  vpc_id      = aws_vpc.gladly_vpc.id

  ingress {
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

  ingress {
    from_port   = 5000
    to_port     = 5000
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  ingress {
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name        = "${var.environment}-sg"
    Environment = var.environment
  }
}

# S3 Bucket for conversation data
resource "aws_s3_bucket" "conversation_data" {
  bucket = "${var.environment}-conversations-${random_id.bucket_suffix.hex}"

  tags = {
    Name        = "${var.environment}-conversations"
    Environment = var.environment
  }
}

resource "aws_s3_bucket_versioning" "conversation_data_versioning" {
  bucket = aws_s3_bucket.conversation_data.id
  versioning_configuration {
    status = "Enabled"
  }
}

resource "random_id" "bucket_suffix" {
  byte_length = 8
}

# IAM Role for EC2
resource "aws_iam_role" "gladly_ec2_role" {
  name = "${var.environment}-ec2-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "ec2://"
        }
      }
    ]
  })

  tags = {
    Name        = "${var.environment}-ec2-role"
    Environment = var.environment
  }
}

resource "aws_iam_instance_profile" "gladly_profile" {
  name = "${var.environment}-ec2-profile"
  role = aws_iam_role.gladly_ec2_role.name

  tags = {
    Name        = "${var.environment}-ec2-profile"
    Environment = var.environment
  }
}

resource "aws_iam_role_policy" "gladly_s3_policy" {
  name = "${var.environment}-s3-policy"
  role = aws_iam_role.gladly_ec2_role.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "s3:GetObject",
          "s3:PutObject",
          "s3:DeleteObject"
        ]
        Resource = "${aws_s3_bucket.conversation_data.arn}/*"
      },
      {
        Effect = "Allow"
        Action = [
          "s3:ListBucket"
        ]
        Resource = aws_s3_bucket.conversation_data.arn
      }
    ]
  })
}

# User data script for EC2
data "template_file" "user_data" {
  template = file("${path.module}/user_data.sh")
  
  vars = {
    github_repository = var.github_repository
    s3_bucket_name    = aws_s3_bucket.conversation_data.bucket
    environment       = var.environment
  }
}

# Key pair
resource "aws_key_pair" "gladly_key_pair" {
  key_name   = "${var.environment}-key-pair"
  public_key = file("~/.ssh/id_rsa.pub")  # Assumes SSH key exists
}

# Launch Template
resource "aws_launch_template" "gladly_template" {
  name_prefix   = "${var.environment}-"
  image_id      = "ami-0c02fb55956c7d316"  # Amazon Linux 2023
  instance_type = var.instance_type
  
  key_name = aws_key_pair.gladly_key_pair.key_name
  
  iam_instance_profile {
    name = aws_iam_instance_profile.gladly_profile.name
  }
  
  vpc_security_group_ids = [aws_security_group.gladly_sg.id]
  
  user_data = base64encode(data.template_file.user_data.rendered)
  
  tag_specifications {
    resource_type = "instance"
    
    tags = {
      Name        = "${var.environment}-instance"
      Environment = var.environment
    }
  }
  
  tags = {
    Name        = "${var.environment}-template"
    Environment = var.environment
  }
}

# Auto Scaling Group
resource "aws_autoscaling_group" "gladly_asg" {
  name                = "${var.environment}-asg"
  vpc_zone_identifier = [aws_subnet.public_subnet.id]
  target_group_arns   = [aws_lb_target_group.gladly_tg.arn]
  health_check_type   = "ELB"
  
  min_size         = 1
  max_size         = 3
  desired_capacity = 1
  
  launch_template {
    id      = aws_launch_template.gladly_template.id
    version = "$Latest"
  }
  
  tag {
    key                 = "Name"
    value               = "${var.environment}-asg-instance"
    propagate_at_launch = false
  }
  
  tag {
    key                 = "Environment"
    value               = var.environment
    propagate_at_launch = false
  }
  
  lifecycle {
    create_before_destroy = true
  }
}

# Application Load Balancer
resource "aws_lb" "gladly_alb" {
  name               = "${var.environment}-alb"
  internal           = false
  load_balancer_type = "application"
  security_groups    = [aws_security_group.gladly_sg.id]
  subnets            = [aws_subnet.public_subnet.id]

  enable_deletion_protection = false

  tags = {
    Name        = "${var.environment}-alb"
    Environment = var.environment
  }
}

resource "aws_lb_target_group" "gladly_tg" {
  name     = "${var.environment}-tg"
  port     = 5000
  protocol = "HTTP"
  vpc_id   = aws_vpc.gladly_vpc.id

  health_check {
    enabled             = true
    healthy_threshold   = 2
    unhealthy_threshold = 2
    timeout             = 5
    interval            = 30
    path                = "/health"
    matcher             = "200"
    port                = "traffic-port"
    protocol            = "HTTP"
  }
}

resource "aws_lb_listener" "gladly_listener" {
  load_balancer_arn = aws_lb.gladly_alb.arn
  port              = "80"
  protocol          = "HTTP"

  default_action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.gladly_tg.arn
  }
}

# Outputs
output "application_url" {
  description = "URL of the deployed application"
  value       = "http://${aws_lb.gladly_alb.dns_name}"
}

output "bucket_name" {
  description = "S3 bucket name for conversation data"
  value       = aws_s3_bucket.conversation_data.bucket
}

output "aws_account_id" {
  description = "AWS Account ID"
  value       = data.aws_caller_identity.current.account_id
}
