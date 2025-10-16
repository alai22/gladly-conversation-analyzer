#!/bin/bash
set -e

echo "🚀 Gladly Deployment Script"
echo "=========================="

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Default values
ENVIRONMENT=${1:-development}
REGION=${2:-us-east-1}
PROJECT_NAME=${3:-gladly-conversation-analyzer}

print_status() {
    echo -e "${GREEN}✓${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}⚠${NC} $1"
}

print_error() {
    echo -e "${RED}✗${NC} $1"
}

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    print_error "Docker is not running. Please start Docker and try again."
    exit 1
fi

print_status "Docker is running"

# Build the Docker image
print_status "Building Docker image..."
docker build -t $PROJECT_NAME:$ENVIRONMENT .

# Check if environment variables are set
if [ -z "$ANTHROPIC_API_KEY" ]; then
    print_warning "ANTHROPIC_API_KEY environment variable is not set"
    print_warning "You'll need to set this in your cloud environment"
fi

if [ -z "$S3_BUCKET_NAME" ] && [ "$ENVIRONMENT" != "development" ]; then
    print_warning "S3_BUCKET_NAME environment variable is not set"
    print_warning "You'll need to set this for cloud deployment"
fi

case $ENVIRONMENT in
    "development")
        print_status "Deploying for development..."
        print_status "Starting container on http://localhost:5000"
        docker run --rm -it \
            -p 5000:5000 \
            -e FLASK_ENV=development \
            -e FLASK_DEBUG=true \
            -v $(pwd)/config_cloud.py:/app/config_local.py:ro \
            --name gladly-dev \
            $PROJECT_NAME:$ENVIRONMENT
        ;;
    
    "production")
        print_status "Deploying for production..."
        print_warning "Make sure to set all required environment variables!"
        print_status "Starting container as daemon..."
        docker run -d \
            -p 80:5000 \
            --restart unless-stopped \
            --name gladly-prod \
            $PROJECT_NAME:$ENVIRONMENT
        
        print_status "Application deployed at http://localhost"
        print_status "Check logs with: docker logs gladly-prod"
        ;;
    
    "ec2")
        print_status "Preparing for EC2 deployment..."
        print_status "Tagging image for AWS ECR (if using)..."
        # Save image as tar file for transfer to EC2
        docker save $PROJECT_NAME:$ENVIRONMENT | gzip > $PROJECT_NAME-$ENVIRONMENT.tar.gz
        print_status "Image saved as $PROJECT_NAME-$ENVIRONMENT.tar.gz"
        print_status "Transfer this file to your EC2 instance and run:"
        echo "  gunzip -c $PROJECT_NAME-$ENVIRONMENT.tar.gz | docker load"
        echo "  docker run -d -p 80:5000 --restart unless-stopped --name gladly-app \\"
        echo "    -e ANTHROPIC_API_KEY=\$ANTHROPIC_API_KEY \\"
        echo "    -e S3_BUCKET_NAME=\$S3_BUCKET_NAME \\"
        echo "    -e AWS_ACCESS_KEY_ID=\$AWS_ACCESS_KEY_ID \\"
        echo "    -e AWS_SECRET_ACCESS_KEY=\$AWS_SECRET_ACCESS_KEY \\"
        echo "    $PROJECT_NAME:$ENVIRONMENT"
        ;;
    
    *)
        print_error "Unknown environment: $ENVIRONMENT"
        print_status "Usage: $0 [development|production|ec2] [region] [project-name]"
        exit 1
        ;;
esac

print_status "Deployment completed!"
