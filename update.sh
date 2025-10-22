#!/bin/bash
echo "🔄 Updating Gladly application..."

# Navigate to project directory
cd ~/gladly-conversation-analyzer

# Pull latest changes
echo "📥 Pulling latest changes from GitHub..."
git pull origin main

# Load environment variables from .env file
if [ -f .env ]; then
    echo "📋 Loading environment variables from .env file..."
    export $(grep -v '^#' .env | xargs)
else
    echo "❌ ERROR: No .env file found!"
    echo "Please create a .env file with your API keys before running this script."
    echo "Example:"
    echo "  ANTHROPIC_API_KEY=your-actual-key"
    echo "  GLADLY_API_KEY=your-actual-key"
    echo "  GLADLY_AGENT_EMAIL=alai@halocollar.com"
    echo "  S3_BUCKET_NAME=your-bucket"
    echo "  AWS_DEFAULT_REGION=us-east-2"
    exit 1
fi

# Stop current container
echo "🛑 Stopping current container..."
docker stop gladly-prod 2>/dev/null || true
docker rm gladly-prod 2>/dev/null || true

# Redeploy
echo "🚀 Redeploying application..."
./deploy.sh production

echo "✅ Update complete!"
