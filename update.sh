#!/bin/bash
echo "🔄 Updating Gladly application..."

# Navigate to project directory
cd ~/gladly-conversation-analyzer

# Pull latest changes
echo "📥 Pulling latest changes from GitHub..."
git pull origin main

# Stop current container
echo "🛑 Stopping current container..."
docker stop gladly-prod 2>/dev/null || true
docker rm gladly-prod 2>/dev/null || true

# Set environment variables
export ANTHROPIC_API_KEY="your-anthropic-api-key-here"
export S3_BUCKET_NAME="your-conversation-bucket-here"
export AWS_DEFAULT_REGION="us-east-2"

# Redeploy
echo "🚀 Redeploying application..."
./deploy.sh production

echo "✅ Update complete!"
