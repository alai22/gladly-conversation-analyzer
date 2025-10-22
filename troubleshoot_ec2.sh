#!/bin/bash
# EC2 Troubleshooting Script for Gladly Deployment

echo "🔍 Gladly EC2 Troubleshooting Script"
echo "===================================="

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

# Check if running as root or with sudo
if [ "$EUID" -eq 0 ]; then
    print_warning "Running as root. Consider using ec2-user for better security."
fi

echo ""
print_info "Step 1: Check Docker Status"
echo "------------------------"

# Check Docker status
if systemctl is-active --quiet docker; then
    print_status "Docker is running"
else
    print_error "Docker is not running"
    echo "Starting Docker..."
    sudo systemctl start docker
    sudo systemctl enable docker
fi

# Check Docker version
docker --version

echo ""
print_info "Step 2: Check Container Status"
echo "----------------------------"

# List all containers
echo "All containers:"
docker ps -a

# Check specifically for gladly-prod
if docker ps -a --format "table {{.Names}}" | grep -q "gladly-prod"; then
    print_status "gladly-prod container exists"
    
    # Check if running
    if docker ps --format "table {{.Names}}" | grep -q "gladly-prod"; then
        print_status "gladly-prod container is running"
    else
        print_error "gladly-prod container is not running"
        echo "Container status:"
        docker ps -a --filter name=gladly-prod
    fi
else
    print_error "gladly-prod container does not exist"
fi

echo ""
print_info "Step 3: Check Container Logs"
echo "---------------------------"

if docker ps -a --format "table {{.Names}}" | grep -q "gladly-prod"; then
    echo "Recent logs from gladly-prod:"
    docker logs gladly-prod --tail 50
    
    echo ""
    echo "Error logs (last 20 lines):"
    docker logs gladly-prod 2>&1 | grep -i "error\|exception\|traceback" | tail -20
    
    echo ""
    echo "S3/Conversation related logs:"
    docker logs gladly-prod 2>&1 | grep -i "s3\|conversation\|backend" | tail -10
else
    print_error "Cannot check logs - container doesn't exist"
fi

echo ""
print_info "Step 4: Check Environment Variables"
echo "--------------------------------"

if docker ps -a --format "table {{.Names}}" | grep -q "gladly-prod"; then
    echo "Environment variables in container:"
    docker exec gladly-prod env | grep -E "(ANTHROPIC|S3|AWS|STORAGE|PORT|HOST)" | sort
else
    print_error "Cannot check environment - container doesn't exist"
fi

echo ""
print_info "Step 5: Check Port Binding"
echo "----------------------"

# Check if port 80 is in use
if netstat -tlnp | grep -q ":80 "; then
    print_status "Port 80 is in use"
    netstat -tlnp | grep ":80 "
else
    print_error "Port 80 is not in use"
fi

# Check if port 5000 is in use
if netstat -tlnp | grep -q ":5000 "; then
    print_status "Port 5000 is in use"
    netstat -tlnp | grep ":5000 "
else
    print_error "Port 5000 is not in use"
fi

echo ""
print_info "Step 6: Check Security Groups"
echo "---------------------------"

# Check if we can reach the application locally
print_info "Testing local connectivity..."

if curl -s -o /dev/null -w "%{http_code}" http://localhost:5000/health 2>/dev/null | grep -q "200"; then
    print_status "Application responds on localhost:5000"
elif curl -s -o /dev/null -w "%{http_code}" http://localhost:80/health 2>/dev/null | grep -q "200"; then
    print_status "Application responds on localhost:80"
else
    print_error "Application does not respond locally"
fi

echo ""
print_info "Step 7: Check Application Files"
echo "-----------------------------"

# Check if application files exist
if [ -d "/home/ec2-user/gladly-conversation-analyzer" ]; then
    print_status "Application directory exists"
    cd /home/ec2-user/gladly-conversation-analyzer
    
    # Check key files
    for file in "app.py" "serve.py" "Dockerfile" "requirements.txt"; do
        if [ -f "$file" ]; then
            print_status "$file exists"
        else
            print_error "$file missing"
        fi
    done
    
    # Check backend directory
    if [ -d "backend" ]; then
        print_status "Backend directory exists"
        ls -la backend/
    else
        print_error "Backend directory missing"
    fi
else
    print_error "Application directory not found"
fi

echo ""
print_info "Step 8: Suggested Fixes"
echo "---------------------"

echo "If the container is not running or has errors:"
echo "1. Stop and remove the existing container:"
echo "   sudo docker stop gladly-prod"
echo "   sudo docker rm gladly-prod"
echo ""
echo "2. Rebuild and restart:"
echo "   cd /home/ec2-user/gladly-conversation-analyzer"
echo "   sudo docker build -t gladly-conversation-analyzer:production ."
echo "   sudo docker run -d -p 80:5000 --restart unless-stopped \\"
echo "     -e ANTHROPIC_API_KEY=\$ANTHROPIC_API_KEY \\"
echo "     -e S3_BUCKET_NAME=\$S3_BUCKET_NAME \\"
echo "     -e AWS_ACCESS_KEY_ID=\$AWS_ACCESS_KEY_ID \\"
echo "     -e AWS_SECRET_ACCESS_KEY=\$AWS_SECRET_ACCESS_KEY \\"
echo "     --name gladly-prod \\"
echo "     gladly-conversation-analyzer:production"
echo ""
echo "3. Check logs:"
echo "   sudo docker logs gladly-prod -f"
echo ""
echo "4. Test the application:"
echo "   curl http://localhost/health"

echo ""
print_info "Troubleshooting completed!"
