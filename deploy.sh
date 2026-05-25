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
PROJECT_NAME=${3:-halo-insight}

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
    echo -e "${GREEN}ℹ${NC} $1"
}

# Free Docker disk when root volume is nearly full (common on small EC2 instances)
maybe_prune_docker_before_build() {
    local use_pct
    use_pct=$(df / | awk 'NR==2 {print $5}' | tr -d '%')
    if [ -n "$use_pct" ] && [ "$use_pct" -ge 90 ]; then
        print_warning "Disk usage at ${use_pct}% — pruning Docker build cache before build..."
        docker builder prune -af >/dev/null 2>&1 || true
    fi
}

prune_docker_after_deploy() {
    print_status "Cleaning up unused Docker images and build cache..."
    docker image prune -af >/dev/null 2>&1 || true
    docker builder prune -af >/dev/null 2>&1 || true
}

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    print_error "Docker is not running. Please start Docker and try again."
    exit 1
fi

print_status "Docker is running"

# Load .env file early if it exists (for production deployments)
if [ "$ENVIRONMENT" = "production" ] && [ -f ".env" ]; then
    print_status "Loading environment variables from .env file..."
    # Load .env file safely, handling comments, empty lines, and quoted values
    while IFS= read -r line || [ -n "$line" ]; do
        # Skip comments and empty lines
        [[ "$line" =~ ^[[:space:]]*# ]] && continue
        [[ -z "${line// }" ]] && continue
        # Remove leading/trailing whitespace
        line=$(echo "$line" | sed 's/^[[:space:]]*//;s/[[:space:]]*$//')
        # Export the variable (handles KEY=value and KEY="value with spaces")
        if [[ "$line" =~ ^([^=]+)=(.*)$ ]]; then
            key="${BASH_REMATCH[1]}"
            value="${BASH_REMATCH[2]}"
            # Remove quotes if present
            value=$(echo "$value" | sed 's/^["'\'']//;s/["'\'']$//')
            export "$key=$value"
        fi
    done < .env
    print_status "Environment variables loaded from .env"
fi

# Build the Docker image
if [ "$ENVIRONMENT" = "production" ]; then
    maybe_prune_docker_before_build
fi
print_status "Building Docker image..."
docker build -t $PROJECT_NAME:$ENVIRONMENT .

# Check if environment variables are set
if [ -z "$ANTHROPIC_API_KEY" ]; then
    print_warning "ANTHROPIC_API_KEY environment variable is not set"
    print_warning "You'll need to set this in your cloud environment"
else
    print_status "ANTHROPIC_API_KEY is set: ${ANTHROPIC_API_KEY:0:12}..."
fi

if [ -z "$GLADLY_API_KEY" ]; then
    print_warning "GLADLY_API_KEY environment variable is not set"
    print_warning "You'll need to set this for Gladly downloads"
else
    print_status "GLADLY_API_KEY is set: ${GLADLY_API_KEY:0:12}..."
fi

if [ -z "$GLADLY_AGENT_EMAIL" ]; then
    print_warning "GLADLY_AGENT_EMAIL environment variable is not set"
    print_warning "You'll need to set this for Gladly downloads"
else
    print_status "GLADLY_AGENT_EMAIL is set: $GLADLY_AGENT_EMAIL"
fi

if [ -z "$S3_BUCKET_NAME" ] && [ "$ENVIRONMENT" != "development" ]; then
    print_warning "S3_BUCKET_NAME environment variable is not set"
    print_warning "You'll need to set this for cloud deployment"
else
    print_status "S3_BUCKET_NAME is set: $S3_BUCKET_NAME"
fi

# Check Survicate API configuration
if [ -z "$SURVICATE_API_KEY" ]; then
    print_warning "SURVICATE_API_KEY environment variable is not set"
    print_warning "API mode will not be available"
else
    print_status "SURVICATE_API_KEY is set: ${SURVICATE_API_KEY:0:12}..."
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
        
        print_warning "Make sure all required environment variables are set!"
        print_status "Starting container as daemon..."
        
        # Remove existing container if present (running or stopped — name must be free)
        print_status "Removing existing container if present..."
        docker rm -f gladly-prod 2>/dev/null || true
        
        # Use --env-file to load all variables from .env (handles spaces and special chars)
        # Also explicitly pass critical variables as -e flags to ensure they're set
        if [ -f ".env" ]; then
            docker run -d \
                -p 127.0.0.1:5000:5000 \
                --restart unless-stopped \
                --env-file .env \
                -e CLAUDE_MODEL="${CLAUDE_MODEL:-claude-haiku-4-5}" \
                -e AWS_DEFAULT_REGION="${AWS_DEFAULT_REGION:-us-east-1}" \
                -e AWS_REGION="${AWS_DEFAULT_REGION:-us-east-1}" \
                -e SURVICATE_API_KEY="${SURVICATE_API_KEY}" \
                -e SURVICATE_WORKSPACE_KEY="${SURVICATE_WORKSPACE_KEY}" \
                -e SURVICATE_WORKSPACE_ID="${SURVICATE_WORKSPACE_ID}" \
                -e SURVICATE_SURVEY_ID="${SURVICATE_SURVEY_ID:-e08c3365f14085e2}" \
                -e SURVICATE_API_BASE_URL="${SURVICATE_API_BASE_URL:-https://api.survicate.com/v1}" \
                -e SURVICATE_CACHE_MAX_AGE_HOURS="${SURVICATE_CACHE_MAX_AGE_HOURS:-24}" \
                --name gladly-prod \
                $PROJECT_NAME:$ENVIRONMENT
        else
            # Fallback to explicit -e flags if .env doesn't exist
            docker run -d \
                -p 127.0.0.1:5000:5000 \
                --restart unless-stopped \
                -e ANTHROPIC_API_KEY="${ANTHROPIC_API_KEY}" \
                -e CLAUDE_MODEL="${CLAUDE_MODEL:-claude-haiku-4-5}" \
                -e GLADLY_API_KEY="${GLADLY_API_KEY}" \
                -e GLADLY_AGENT_EMAIL="${GLADLY_AGENT_EMAIL}" \
                -e S3_BUCKET_NAME="${S3_BUCKET_NAME}" \
                -e AWS_DEFAULT_REGION="${AWS_DEFAULT_REGION:-us-east-1}" \
                -e AWS_REGION="${AWS_DEFAULT_REGION:-us-east-1}" \
                -e SURVICATE_API_KEY="${SURVICATE_API_KEY}" \
                -e SURVICATE_SURVEY_ID="${SURVICATE_SURVEY_ID:-e08c3365f14085e2}" \
                -e SURVICATE_WORKSPACE_KEY="${SURVICATE_WORKSPACE_KEY}" \
                -e SURVICATE_WORKSPACE_ID="${SURVICATE_WORKSPACE_ID}" \
                -e SURVICATE_API_BASE_URL="${SURVICATE_API_BASE_URL:-https://api.survicate.com/v1}" \
                -e SURVICATE_CACHE_MAX_AGE_HOURS="${SURVICATE_CACHE_MAX_AGE_HOURS:-24}" \
                --name gladly-prod \
                $PROJECT_NAME:$ENVIRONMENT
        fi
        
        print_status "Application deployed on localhost:5000 (nginx proxies HTTPS to this)"
        print_status "Access via HTTPS: https://your-ip-or-domain"
        print_status "Check logs with: docker logs gladly-prod"
        prune_docker_after_deploy
        print_info "Note: Using IAM role for S3 access (no AWS credentials needed)"
        print_info "Note: Nginx handles ports 80/443, Docker runs on localhost:5000"
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
        echo "    -e GLADLY_API_KEY=\$GLADLY_API_KEY \\"
        echo "    -e GLADLY_AGENT_EMAIL=\$GLADLY_AGENT_EMAIL \\"
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
