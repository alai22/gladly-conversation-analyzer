#!/bin/bash

# One-time HTTPS Infrastructure Setup Script
# This script sets up HTTPS infrastructure and then uses your existing deploy.sh

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

print_status() {
    echo -e "${GREEN}✓${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}⚠${NC} $1"
}

print_error() {
    echo -e "${RED}✗${NC} $1"
}

print_info() {
    echo -e "${BLUE}ℹ${NC} $1"
}

# Default values
ENVIRONMENT="gladly-prod"
AWS_REGION="us-east-1"

echo "🚀 HTTPS Infrastructure Setup (One-time)"
echo "========================================"
echo "This script will:"
echo "  1. Set up HTTPS infrastructure with Terraform"
echo "  2. Work with your existing Git-based deployment workflow"
echo "  3. Work with your .env file on EC2"
echo ""
echo "Your workflow:"
echo "  Local: git push origin main"
echo "  EC2:  git pull origin main → ./deploy.sh production"
echo ""

# Check prerequisites
print_info "Checking prerequisites..."

# Check if AWS CLI is installed
if ! command -v aws &> /dev/null; then
    print_error "AWS CLI is not installed. Please install it first."
    exit 1
fi
print_status "AWS CLI is installed"

# Check if Terraform is installed
if ! command -v terraform &> /dev/null; then
    print_error "Terraform is not installed. Please install it first."
    exit 1
fi
print_status "Terraform is installed"

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    print_error "Docker is not running. Please start Docker and try again."
    exit 1
fi
print_status "Docker is running"

# Check AWS credentials
if ! aws sts get-caller-identity &> /dev/null; then
    print_error "AWS credentials not configured. Please run 'aws configure' first."
    exit 1
fi
print_status "AWS credentials configured"

# Check if IAM role exists
print_info "Checking IAM role GladlyS3FA..."
if ! aws iam get-role --role-name GladlyS3FA &> /dev/null; then
    print_error "IAM role 'GladlyS3FA' not found. Please create this role first."
    exit 1
fi
print_status "IAM role GladlyS3FA found"

# Check if .env file exists
if [ ! -f ".env" ]; then
    print_warning ".env file not found. You'll need to create one on your EC2 instance."
    print_info "Create .env file with your environment variables on EC2"
else
    print_status ".env file found"
fi

# Create terraform.tfvars file
print_info "Creating Terraform configuration..."

cat > terraform/terraform.tfvars << EOF
environment = "$ENVIRONMENT"
aws_region = "$AWS_REGION"
EOF

print_status "Terraform configuration created"

# Deploy infrastructure
print_info "Deploying HTTPS infrastructure with Terraform..."

cd terraform

# Initialize Terraform
print_status "Initializing Terraform..."
terraform init

# Plan deployment
print_status "Planning infrastructure deployment..."
terraform plan

# Ask for confirmation
echo ""
print_warning "This will set up HTTPS infrastructure (one-time setup)."
print_warning "It will use your existing IAM role 'GladlyS3FA' for S3 access."
print_warning "Continue? (y/N)"
read -r response
if [[ ! "$response" =~ ^[Yy]$ ]]; then
    print_info "Infrastructure setup cancelled by user"
    exit 0
fi

# Apply changes
print_status "Applying Terraform changes..."
terraform apply -auto-approve

# Get outputs
print_status "Getting deployment outputs..."
APP_URL=$(terraform output -raw application_url)
APP_URL_HTTP=$(terraform output -raw application_url_http)
LB_DNS=$(echo $APP_URL | sed 's|https://||')

print_status "HTTPS infrastructure deployed successfully!"

# Go back to project root
cd ..

# Display results
echo ""
echo "🎉 HTTPS Infrastructure Setup Complete!"
echo "======================================"
echo ""
print_status "Your HTTPS infrastructure is now ready:"
echo "  HTTPS: $APP_URL"
echo "  HTTP:  $APP_URL_HTTP (redirects to HTTPS)"
echo ""

print_info "Next steps:"
echo "  1. Make sure your .env file exists on EC2"
echo "  2. Deploy your application:"
echo "     ./deploy.sh production"
echo ""

print_info "Your .env file should contain:"
echo "  ANTHROPIC_API_KEY=your-key"
echo "  GLADLY_API_KEY=your-key"
echo "  GLADLY_AGENT_EMAIL=your-email"
echo "  S3_BUCKET_NAME=your-bucket"
echo "  # Note: No AWS credentials needed (using IAM role)"
echo ""

print_info "For future deployments, use your Git workflow:"
echo "  Local: git push origin main"
echo "  EC2:  git pull origin main"
echo "  EC2:  ./deploy.sh production"
echo ""

print_status "HTTPS infrastructure setup completed!"
print_info "The infrastructure is now ready for your application deployments."
