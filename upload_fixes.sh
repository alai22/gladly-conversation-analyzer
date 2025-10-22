#!/bin/bash
# Script to upload fixed files and rebuild the container

echo "🔧 Uploading fixed files to EC2..."

# Upload the fixed files
scp -i your-key.pem backend/api/routes/rag_routes.py ec2-user@3.150.69.20:~/gladly-conversation-analyzer/backend/api/routes/
scp -i your-key.pem backend/api/routes/health_routes.py ec2-user@3.150.69.20:~/gladly-conversation-analyzer/backend/api/routes/
scp -i your-key.pem backend/api/routes/conversation_routes.py ec2-user@3.150.69.20:~/gladly-conversation-analyzer/backend/api/routes/
scp -i your-key.pem backend/api/routes/claude_routes.py ec2-user@3.150.69.20:~/gladly-conversation-analyzer/backend/api/routes/
scp -i your-key.pem backend/api/middleware/error_handlers.py ec2-user@3.150.69.20:~/gladly-conversation-analyzer/backend/api/middleware/

echo "✅ Files uploaded successfully!"
echo ""
echo "Now SSH into your EC2 and run:"
echo "cd ~/gladly-conversation-analyzer"
echo "sudo docker stop gladly-prod"
echo "sudo docker rm gladly-prod"
echo "sudo docker build -t gladly-conversation-analyzer:production ."
echo "sudo docker run -d -p 80:5000 --restart unless-stopped \\"
echo "  -e ANTHROPIC_API_KEY=\$ANTHROPIC_API_KEY \\"
echo "  -e S3_BUCKET_NAME=\$S3_BUCKET_NAME \\"
echo "  -e AWS_ACCESS_KEY_ID=\$AWS_ACCESS_KEY_ID \\"
echo "  -e AWS_SECRET_ACCESS_KEY=\$AWS_SECRET_ACCESS_KEY \\"
echo "  --name gladly-prod \\"
echo "  gladly-conversation-analyzer:production"
