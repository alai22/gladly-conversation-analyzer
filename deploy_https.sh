#!/bin/bash

# HTTPS Deployment Script for Gladly Conversation Analyzer
# This script helps deploy your application with HTTPS support

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
DOMAIN_NAME=""
CERTIFICATE_ARN=""
ENVIRONMENT="gladly-prod"
AWS_REGION="us-east-1"

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --domain)
            DOMAIN_NAME="$2"
            shift 2
            ;;
        --certificate-arn)
            CERTIFICATE_ARN="$2"
            shift 2
            ;;
        --environment)
            ENVIRONMENT="$2"
            shift 2
            ;;
        --region)
            AWS_REGION="$2"
            shift 2
            ;;
        --help)
            echo "Usage: $0 [OPTIONS]"
            echo ""
            echo "Options:"
            echo "  --domain DOMAIN          Custom domain name (optional)"
            echo "  --certificate-arn ARN    Existing SSL certificate ARN (optional)"
            echo "  --environment ENV        Environment name (default: gladly-prod)"
            echo "  --region REGION          AWS region (default: us-east-1)"
            echo "  --help                   Show this help message"
            echo ""
            echo "Examples:"
            echo "  $0                                    # Deploy with AWS default certificate"
            echo "  $0 --domain myapp.com                # Deploy with custom domain"
            echo "  $0 --certificate-arn arn:aws:acm:... # Deploy with existing certificate"
            exit 0
            ;;
        *)
            print_error "Unknown option: $1"
            echo "Use --help for usage information"
            exit 1
            ;;
    esac
done

echo "🚀 HTTPS Deployment Script for Gladly Conversation Analyzer"
echo "============================================================"

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

# Check required environment variables
print_info "Checking environment variables..."

REQUIRED_VARS=("ANTHROPIC_API_KEY" "GLADLY_API_KEY" "GLADLY_AGENT_EMAIL" "S3_BUCKET_NAME" "AWS_ACCESS_KEY_ID" "AWS_SECRET_ACCESS_KEY")

for var in "${REQUIRED_VARS[@]}"; do
    if [ -z "${!var}" ]; then
        print_error "Required environment variable $var is not set"
        exit 1
    else
        print_status "$var is set"
    fi
done

# Create terraform.tfvars file
print_info "Creating Terraform configuration..."

cat > terraform/terraform.tfvars << EOF
environment = "$ENVIRONMENT"
aws_region = "$AWS_REGION"
EOF

if [ -n "$DOMAIN_NAME" ]; then
    echo "domain_name = \"$DOMAIN_NAME\"" >> terraform/terraform.tfvars
    print_status "Custom domain configured: $DOMAIN_NAME"
fi

if [ -n "$CERTIFICATE_ARN" ]; then
    echo "certificate_arn = \"$CERTIFICATE_ARN\"" >> terraform/terraform.tfvars
    print_status "Existing certificate configured: $CERTIFICATE_ARN"
fi

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
print_warning "This will deploy/update your AWS infrastructure. Continue? (y/N)"
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
    -e AWS_ACCESS_KEY_ID="${AWS_ACCESS_KEY_ID}" \
    -e AWS_SECRET_ACCESS_KEY="${AWS_SECRET_ACCESS_KEY}" \
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

if [ -n "$DOMAIN_NAME" ]; then
    echo "Custom domain: https://$DOMAIN_NAME"
    echo ""
    print_warning "Don't forget to configure your DNS:"
    echo "  Create a CNAME record pointing $DOMAIN_NAME to $LB_DNS"
    echo ""
fi

print_info "Useful commands:"
echo "  Check application logs: docker logs gladly-prod"
echo "  Check load balancer: aws elbv2 describe-load-balancers --region $AWS_REGION"
echo "  Test HTTPS: curl -I $APP_URL"
echo ""

print_status "HTTPS deployment completed successfully!"

