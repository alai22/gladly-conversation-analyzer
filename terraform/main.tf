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
variable "domain_name" {
  description = "Domain name for SSL certificate (optional)"
  type        = string
  default     = ""
}

variable "certificate_arn" {
  description = "ARN of existing SSL certificate (optional)"
  type        = string
  default     = ""
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

resource "aws_subnet" "public_subnet_1" {
  vpc_id                  = aws_vpc.gladly_vpc.id
  cidr_block              = "10.0.10.0/24"
  availability_zone       = data.aws_availability_zones.available.names[0]
  map_public_ip_on_launch = true

  tags = {
    Name        = "${var.environment}-public-subnet-1"
    Environment = var.environment
  }
}

resource "aws_subnet" "public_subnet_2" {
  vpc_id                  = aws_vpc.gladly_vpc.id
  cidr_block              = "10.0.11.0/24"
  availability_zone       = data.aws_availability_zones.available.names[1]
  map_public_ip_on_launch = true

  tags = {
    Name        = "${var.environment}-public-subnet-2"
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

resource "aws_route_table_association" "public_rta_1" {
  subnet_id      = aws_subnet.public_subnet_1.id
  route_table_id = aws_route_table.public_rt.id
}

resource "aws_route_table_association" "public_rta_2" {
  subnet_id      = aws_subnet.public_subnet_2.id
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

# Use existing IAM role GladlyS3FA
data "aws_iam_role" "gladly_s3_role" {
  name = "GladlyS3FA"
}

resource "aws_iam_instance_profile" "gladly_profile" {
  name = "${var.environment}-ec2-profile"
  role = data.aws_iam_role.gladly_s3_role.name

  tags = {
    Name        = "${var.environment}-ec2-profile"
    Environment = var.environment
  }
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
  vpc_zone_identifier = [aws_subnet.public_subnet_1.id, aws_subnet.public_subnet_2.id]
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
  subnets            = [aws_subnet.public_subnet_1.id, aws_subnet.public_subnet_2.id]

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

# SSL Certificate (if domain_name is provided)
resource "aws_acm_certificate" "gladly_cert" {
  count = var.domain_name != "" ? 1 : 0
  
  domain_name       = var.domain_name
  validation_method = "DNS"

  lifecycle {
    create_before_destroy = true
  }

  tags = {
    Name        = "${var.environment}-cert"
    Environment = var.environment
  }
}

# Certificate validation (if domain_name is provided)
resource "aws_acm_certificate_validation" "gladly_cert_validation" {
  count = var.domain_name != "" ? 1 : 0
  
  certificate_arn         = aws_acm_certificate.gladly_cert[0].arn
  validation_record_fqdns = [for record in aws_route53_record.gladly_cert_validation : record.fqdn]
}

# Route53 record for certificate validation (if domain_name is provided)
resource "aws_route53_record" "gladly_cert_validation" {
  for_each = var.domain_name != "" ? {
    for dvo in aws_acm_certificate.gladly_cert[0].domain_validation_options : dvo.domain_name => {
      name   = dvo.resource_record_name
      record = dvo.resource_record_value
      type   = dvo.resource_record_type
    }
  } : {}

  allow_overwrite = true
  name            = each.value.name
  records         = [each.value.record]
  ttl             = 60
  type            = each.value.type
  zone_id         = data.aws_route53_zone.main[0].zone_id
}

# Route53 zone lookup (if domain_name is provided)
data "aws_route53_zone" "main" {
  count = var.domain_name != "" ? 1 : 0
  name  = var.domain_name
}

# HTTP listener (redirects to HTTPS)
resource "aws_lb_listener" "gladly_listener_http" {
  load_balancer_arn = aws_lb.gladly_alb.arn
  port              = "80"
  protocol          = "HTTP"

  default_action {
    type = "redirect"

    redirect {
      port        = "443"
      protocol    = "HTTPS"
      status_code = "HTTP_301"
    }
  }
}

# HTTPS listener
resource "aws_lb_listener" "gladly_listener_https" {
  load_balancer_arn = aws_lb.gladly_alb.arn
  port              = "443"
  protocol          = "HTTPS"
  ssl_policy        = "ELBSecurityPolicy-TLS-1-2-2017-01"
  certificate_arn   = var.certificate_arn != "" ? var.certificate_arn : (var.domain_name != "" ? aws_acm_certificate_validation.gladly_cert_validation[0].certificate_arn : null)

  default_action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.gladly_tg.arn
  }
}

# Outputs
output "application_url" {
  description = "URL of the deployed application"
  value       = "https://${aws_lb.gladly_alb.dns_name}"
}

output "application_url_http" {
  description = "HTTP URL of the deployed application (redirects to HTTPS)"
  value       = "http://${aws_lb.gladly_alb.dns_name}"
}

output "application_url_custom_domain" {
  description = "Custom domain URL (if domain_name is provided)"
  value       = var.domain_name != "" ? "https://${var.domain_name}" : null
}

output "ssl_certificate_arn" {
  description = "ARN of the SSL certificate"
  value       = var.certificate_arn != "" ? var.certificate_arn : (var.domain_name != "" ? aws_acm_certificate.gladly_cert[0].arn : null)
}

output "bucket_name" {
  description = "S3 bucket name for conversation data"
  value       = aws_s3_bucket.conversation_data.bucket
}

output "aws_account_id" {
  description = "AWS Account ID"
  value       = data.aws_caller_identity.current.account_id
}
