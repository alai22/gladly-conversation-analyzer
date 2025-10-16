# Variables for Gladly Terraform configuration

variable "aws_region" {
  description = "AWS region to deploy resources"
  type        = string
  default     = "us-east-1"
  
  validation {
    condition     = can(regex("^[a-z][a-z-]+[a-z]$", var.aws_region))
    error_message = "AWS region must be a valid region format."
  }
}

variable "environment" {
  description = "Environment name (e.g., dev, staging, prod)"
  type        = string
  default     = "gladly-prod"
  
  validation {
    condition     = can(regex("^[a-z][a-z0-9-]*$", var.environment))
    error_message = "Environment name must be lowercase alphanumeric with hyphens only."
  }
}

variable "instance_type" {
  description = "EC2 instance type for Gladly application"
  type        = string
  default     = "t3.medium"
  
  validation {
    condition = contains([
      "t2.micro", "t2.small", "t2.medium", "t3.small", "t3.medium", 
      "t3.large", "m5.large", "m5.xlarge", "c5.large", "c5.xlarge"
    ], var.instance_type)
    error_message = "Invalid instance type for Gladly application."
  }
}

variable "github_repository" {
  description = "GitHub repository URL for cloning"
  type        = string
  default     = "https://github.com/YOUR_USERNAME/gladly-conversation-analyzer"
  
  validation {
    condition     = can(regex("^https://github\\.com/.+", var.github_repository))
    error_message = "Must be a valid GitHub repository URL."
  }
}

variable "allow_ssh_access" {
  description = "Allow SSH access to EC2 instances"
  type        = bool
  default     = true
}

variable "min_instance_count" {
  description = "Minimum number of instances in Auto Scaling Group"
  type        = number
  default     = 1
  
  validation {
    condition     = var.min_instance_count >= 1 && var.min_instance_count <= 10
    error_message = "Minimum instance count must be between 1 and 10."
  }
}

variable "max_instance_count" {
  description = "Maximum number of instances in Auto Scaling Group"
  type        = number
  default     = 3
  
  validation {
    condition     = var.max_instance_count >= 1 && var.max_instance_count <= 10
    error_message = "Maximum instance count must be between 1 and 10."
  }
}

variable "desired_instance_count" {
  description = "Desired number of instances in Auto Scaling Group"
  type        = number
  default     = 1
  
  validation {
    condition     = var.desired_instance_count >= var.min_instance_count && var.desired_instance_count <= var.max_instance_count
    error_message = "Desired instance count must be between min and max counts."
  }
}

variable "enable_auto_scaling" {
  description = "Enable auto scaling for the application"
  type        = bool
  default     = false
}

variable "enable_load_balancer" {
  description = "Enable Application Load Balancer"
  type        = bool
  default     = true
}

variable "health_check_grace_period" {
  description = "Health check grace period in seconds"
  type        = number
  default     = 300
}

variable "enable_detailed_monitoring" {
  description = "Enable detailed CloudWatch monitoring"
  type        = bool
  default     = false
}

variable "conversation_data_retention_days" {
  description = "Number of days to retain conversation data backups"
  type        = number
  default     = 30
  
  validation {
    condition     = var.conversation_data_retention_days >= 7 && var.conversation_data_retention_days <= 365
    error_message = "Retention period must be between 7 and 365 days."
  }
}
