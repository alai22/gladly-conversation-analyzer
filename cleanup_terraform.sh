#!/bin/bash

# Cleanup Terraform Resources
# Use this script to remove Terraform-created infrastructure

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

echo "🧹 Terraform Cleanup Script"
echo "=========================="
echo ""
print_warning "This will destroy all Terraform-managed infrastructure!"
print_info "This includes: VPC, subnets, load balancer, security groups, etc."
echo ""

# Check if terraform directory exists
if [ ! -d "terraform" ]; then
    print_error "terraform directory not found"
    exit 1
fi

# Check if terraform is initialized
cd terraform
if [ ! -f "terraform.tfstate" ] && [ ! -f ".terraform/terraform.tfstate" ]; then
    print_info "No Terraform state found. Nothing to clean up."
    exit 0
fi

# Show what will be destroyed
print_info "Checking what Terraform has created..."
terraform plan -destroy

echo ""
print_warning "This will permanently delete all Terraform-managed resources!"
read -p "Are you sure you want to proceed? (type 'yes' to confirm): " CONFIRM

if [ "$CONFIRM" != "yes" ]; then
    print_info "Cleanup cancelled"
    exit 0
fi

# Destroy resources
print_status "Destroying Terraform resources..."
terraform destroy -auto-approve

if [ $? -eq 0 ]; then
    print_status "Terraform resources destroyed successfully!"
    
    # Optional: Remove Terraform state files
    echo ""
    read -p "Remove Terraform state files and .terraform directory? (y/N): " REMOVE_STATE
    
    if [[ "$REMOVE_STATE" =~ ^[Yy]$ ]]; then
        print_status "Removing Terraform state files..."
        rm -rf .terraform
        rm -f terraform.tfstate terraform.tfstate.backup .terraform.lock.hcl
        rm -f terraform.tfvars
        print_status "State files removed"
    fi
else
    print_error "Failed to destroy some resources. Check the output above."
    exit 1
fi

cd ..

echo ""
print_status "Cleanup complete!"
print_info "You can now use the nginx-based HTTPS setup without conflicts."
