#!/bin/bash

# User data script for EC2 instance
# This script installs Docker, clones the repository, and deploys Gladly

set -e

# Update system
yum update -y

# Install Docker
yum install -y docker
systemctl start docker
systemctl enable docker
usermod -a -G docker ec2-user

# Install Git
yum install -y git

# Install Docker Compose
curl -L "https://github.com/docker/compose/releases/download/v2.21.0/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
chmod +x /usr/local/bin/docker-compose

# Clone repository
cd /home/ec2-user
git clone ${github_repository} gladly-conversation-analyzer
cd gladly-conversation-analyzer

# Create environment file from template
if [ ! -f .env ]; then
    cp env.example .env
fi

# Log any custom logs to a file
echo "Environment: ${environment}" >> /var/log/gladly-deploy.log
echo "Repository: ${github_repository}" >> /var/log/gladly-deploy.log
echo "S3 Bucket: ${s3_bucket_name}" >> /var/log/gladly-deploy.log

# Make deployment script executable
chmod +x deploy.sh

# Set environment variables for deployment
export S3_BUCKET_NAME="${s3_bucket_name}"
export AWS_DEFAULT_REGION="us-east-1"

# Create a startup script that will run the deployment
cat > /home/ec2-user/start-gladly.sh << 'EOF'
#!/bin/bash
set -e

cd /home/ec2-user/gladly-conversation-analyzer

# Log startup
echo "Starting Gladly deployment at $(date)" >> /var/log/gladly-deploy.log

# Check if ANTHROPIC_API_KEY is set
if [ -z "$ANTHROPIC_API_KEY" ]; then
    echo "ANTHROPIC_API_KEY not set. Please set this environment variable." >> /var/log/gladly-deploy.log
    exit 1
fi

# Deploy the application
echo "Deploying Gladly application..." >> /var/log/gladly-deploy.log
./deploy.sh production >> /var/log/gladly-deploy.log 2>&1

echo "Gladly deployment completed at $(date)" >> /var/log/gladly-deploy.log
EOF

chmod +x /home/ec2-user/start-gladly.sh

# Add startup command to crontab to run on boot
echo "@reboot ec2-user /home/ec2-user/start-gladly.sh" | crontab -u ec2-user -

# Clean up
rm -rf /tmp/*

echo "Bootstrap completed successfully" >> /var/log/gladly-deploy.log
