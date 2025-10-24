#!/bin/bash

# HTTPS Deployment Script for Gladly Conversation Analyzer (IP-based with existing IAM role)
# This script deploys HTTPS using your existing IAM role GladlyS3FA

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

echo "🚀 HTTPS Deployment Script for Gladly Conversation Analyzer"
echo "============================================================"
echo "Using existing IAM role: GladlyS3FA"
echo "Deployment type: IP-based (no custom domain)"
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

# Check required environment variables
print_info "Checking environment variables..."

REQUIRED_VARS=("ANTHROPIC_API_KEY" "GLADLY_API_KEY" "GLADLY_AGENT_EMAIL" "S3_BUCKET_NAME")

for var in "${REQUIRED_VARS[@]}"; do
    if [ -z "${!var}" ]; then
        print_error "Required environment variable $var is not set"
        exit 1
    else
        print_status "$var is set"
    fi
done

# Note: We don't need AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY since we're using IAM role
print_info "Using IAM role for S3 access (no AWS credentials needed in environment)"

# Create terraform.tfvars file
print_info "Creating Terraform configuration..."

cat > terraform/terraform.tfvars << EOF
environment = "$ENVIRONMENT"
aws_region = "$AWS_REGION"
EOF

print_status "Terraform configuration created"

# Deploy infrastructure
print_info "Deploying infrastructure with Terraform..."

cd terraform

# Initialize Terraform
print_status "Initializing Terraform..."
terraform init

# Plan deployment
print_status "Planning deployment..."
terraform plan

# Ask for confirmation
echo ""
print_warning "This will deploy/update your AWS infrastructure with HTTPS support."
print_warning "It will use your existing IAM role 'GladlyS3FA' for S3 access."
print_warning "Continue? (y/N)"
read -r response
if [[ ! "$response" =~ ^[Yy]$ ]]; then
    print_info "Deployment cancelled by user"
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

print_status "Infrastructure deployed successfully!"

# Go back to project root
cd ..

# Deploy application
print_info "Deploying application..."

# Build and deploy the application
print_status "Building Docker image..."
docker build -t gladly-conversation-analyzer:$ENVIRONMENT .

# Stop existing container if running
if docker ps -q -f name=gladly-prod | grep -q .; then
    print_status "Stopping existing container..."
    docker stop gladly-prod
    docker rm gladly-prod
fi

print_status "Deploying application container..."
docker run -d \
    -p 80:5000 \
    --restart unless-stopped \
    -e ANTHROPIC_API_KEY="${ANTHROPIC_API_KEY}" \
    -e GLADLY_API_KEY="${GLADLY_API_KEY}" \
    -e GLADLY_AGENT_EMAIL="${GLADLY_AGENT_EMAIL}" \
    -e S3_BUCKET_NAME="${S3_BUCKET_NAME}" \
    -e AWS_DEFAULT_REGION="${AWS_REGION}" \
    -e AWS_REGION="${AWS_REGION}" \
    --name gladly-prod \
    gladly-conversation-analyzer:$ENVIRONMENT

# Wait for application to start
print_status "Waiting for application to start..."
sleep 30

# Test the deployment
print_info "Testing deployment..."

# Test HTTP (should redirect to HTTPS)
print_status "Testing HTTP endpoint..."
HTTP_STATUS=$(curl -s -o /dev/null -w "%{http_code}" $APP_URL_HTTP)
if [ "$HTTP_STATUS" = "301" ] || [ "$HTTP_STATUS" = "302" ]; then
    print_status "HTTP redirect working (status: $HTTP_STATUS)"
else
    print_warning "HTTP redirect may not be working (status: $HTTP_STATUS)"
fi

# Test HTTPS
print_status "Testing HTTPS endpoint..."
HTTPS_STATUS=$(curl -s -o /dev/null -w "%{http_code}" $APP_URL)
if [ "$HTTPS_STATUS" = "200" ]; then
    print_status "HTTPS endpoint working (status: $HTTPS_STATUS)"
else
    print_warning "HTTPS endpoint may not be working (status: $HTTPS_STATUS)"
fi

# Display results
echo ""
echo "🎉 Deployment Complete!"
echo "======================="
echo ""
print_status "Your application is now available at:"
echo "  HTTPS: $APP_URL"
echo "  HTTP:  $APP_URL_HTTP (redirects to HTTPS)"
echo ""

print_info "Key changes made:"
echo "  ✓ HTTPS enabled with SSL certificate"
echo "  ✓ HTTP traffic redirected to HTTPS"
echo "  ✓ Using existing IAM role 'GladlyS3FA' for S3 access"
echo "  ✓ No more public S3 bucket access needed"
echo ""

print_info "Useful commands:"
echo "  Check application logs: docker logs gladly-prod"
echo "  Check load balancer: aws elbv2 describe-load-balancers --region $AWS_REGION"
echo "  Test HTTPS: curl -I $APP_URL"
echo "  Test S3 access: docker exec gladly-prod aws s3 ls s3://$S3_BUCKET_NAME"
echo ""

print_status "HTTPS deployment with IAM role completed successfully!"
