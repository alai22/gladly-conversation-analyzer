# Deployment Guide for Gladly Conversation Analyzer

This guide covers deploying the Gladly application to GitHub, EC2, and S3 for version control and private cloud hosting.

## Prerequisites

### Required Software
- [Git](https://git-scm.com/downloads) - Version control
- [Docker](https://www.docker.com/get-started) - Containerization
- [Node.js](https://nodejs.org/) - Frontend dependencies
- [Python 3.11+](https://python.org/downloads/) - Backend runtime

### Required API Keys and Credentials
- Anthropic API key for Claude access
- AWS credentials (if using S3 storage)
- Azure credentials (if using Azure Blob Storage)

## 1. Setting Up Version Control (GitHub)

### Initial Git Setup
```bash
# Initialize git repository (if not already done)
git init

# Add all files to git
git add .

# Commit initial version
git commit -m "Initial commit: Gladly conversation analyzer"

# Create repository on GitHub, then connect:
git remote add origin https://github.com/YOUR_USERNAME/gladly-conversation-analyzer.git
git branch -M main
git push -u origin main
```

### Environment Configuration
1. Copy the example environment file:
```bash
cp env.example .env
```

2. Edit `.env` with your actual values:
```bash
# Required
ANTHROPIC_API_KEY=your-actual-key-here

# For S3 deployment
S3_BUCKET_NAME=your-actual-bucket-name
AWS_ACCESS_KEY_ID=your-access-key
AWS_SECRET_ACCESS_KEY=your-secret-key
```

## 2. Local Development Setup

### Python Environment
```bash
# Create virtual environment
python -m venv venv

# Activate virtual environment
source venv/bin/activate  # On Windows: venv\\Scripts\\activate

# Install dependencies
pip install -r requirements.txt
```

### Frontend Setup
```bash
# Install Node.js dependencies
npm install

# Build the React frontend
npm run build
```

### Running Locally
```bash
# Option 1: Using the deployment script
chmod +x deploy.sh
./deploy.sh development

# Option 2: Manual startup
# Terminal 1 (Backend)
# On Linux/Mac:
source venv/bin/activate && python app.py
# On Windows:
venv\Scripts\activate && python app.py

# Terminal 2 (Frontend - if developing)
npm start
```

## 3. Cloud Deployment Options

### Option A: EC2 Deployment

#### Step 1: Prepare EC2 Instance
1. Launch an Amazon Linux 2023 EC2 instance with:
   - Instance type: t3.medium or larger (recommended for AI processing)
   - Security groups: Allow inbound HTTP (80) and HTTPS (443) traffic
   - Storage: At least 20GB

2. Connect to your EC2 instance:
```bash
ssh -i your-key.pem ec2-user@your-ec2-public-ip
```

#### Step 2: Install Docker on EC2
```bash
# Update system
sudo yum update -y

# Install Docker
sudo yum install docker -y
sudo service docker start
sudo usermod -a -G docker ec2-user

# Log out and back in to apply group changes
exit
# SSH back in
```

#### Step 3: Deploy Application
```bash
# Clone your repository
git clone https://github.com/YOUR_USERNAME/gladly-conversation-analyzer.git
cd gladly-conversation-analyzer

# Build and deploy
chmod +x deploy.sh
export ANTHROPIC_API_KEY="your-api-key"
export S3_BUCKET_NAME="your-bucket-name"
export AWS_ACCESS_KEY_ID="your-access-key"
export AWS_SECRET_ACCESS_KEY="your-secret-key"
./deploy.sh production

# Or transfer pre-built image from local machine:
# From local machine:
docker save gladly-conversation-analyzer:production | gzip > gladly-production.tar.gz
scp -i your-key.pem gladly-production.tar.gz ec2-user@your-ec2-ip:~/

# On EC2:
gunzip -c gladly-production.tar.gz | sudo docker load
sudo docker run -d -p 80:5000 --restart unless-stopped \
  --name gladly-app \
  -e ANTHROPIC_API_KEY="$ANTHROPIC_API_KEY" \
  -e S3_BUCKET_NAME="$S3_BUCKET_NAME" \
  gladly-conversation-analyzer:production
```

#### Step 4: Set up Auto-scaling (Optional)
For high availability, consider using:
- AWS Application Load Balancer
- Auto Scaling Groups
- ECS or EKS for container orchestration

### Option B: S3 Static Hosting + Lambda

For a serverless approach:

#### Step 1: Build Static Frontend
```bash
# Build production React app
npm run build

# Upload to S3 bucket configured for static website hosting
aws s3 sync build/ s3://your-website-bucket --delete
```

#### Step 2: Create Lambda Function
```bash
# Create deployment package
pip install -r requirements.txt -t ./lambda_package/
cp *.py ./lambda_package/
zip -r lambda-deployment.zip ./lambda_package/

# Upload to AWS Lambda via AWS Console or CLI
aws lambda create-function \
  --function-name gladly-api \
  --runtime python3.11 \
  --role arn:aws:iam::ACCOUNT:role/lambda-execution-role \
  --handler app.lambda_handler \
  --zip-file fileb://lambda-deployment.zip
```

### Option C: Docker Containers

#### Using Docker Compose (Local Cloud)
```bash
# Set environment variables
export ANTHROPIC_API_KEY="your-key"
export S3_BUCKET_NAME="your-bucket"
export AWS_ACCESS_KEY_ID="your-key"
export AWS_SECRET_ACCESS_KEY="your-secret"

# Start services
docker-compose up -d

# Check status
docker-compose ps
docker-compose logs gladly-app
```

## 4. Production Considerations

### Security
- Use environment variables for all secrets
- Enable HTTPS/TLS certificates (Let's Encrypt or AWS Certificate Manager)
- Configure firewalls and security groups appropriately
- Regular security updates

### Monitoring
- Set up CloudWatch or similar monitoring
- Configure health check intervals
- Monitor API usage and costs

### Backups
- Regular backup of conversation data
- Version control all configuration changes
- Test disaster recovery procedures

### Scaling
- Monitor resource usage
- Plan for horizontal scaling if needed
- Consider CDN for static assets

## 5. Environment-Specific Configuration

### Development
```bash
./deploy.sh development
```
- Runs with debug mode enabled
- Mounts local config files
- Uses local port 5000

### Production
```bash
./deploy.sh production
```
- Runs as daemon process
- Uses port 80
- Automatic restart on failure
- Optimized for performance

## Troubleshooting

### Common Issues

1. **API Key Not Working**
   - Verify environment variable is set correctly
   - Check Anthropic API key validity
   - Ensure proper permissions

2. **S3 Access Denied**
   - Verify AWS credentials
   - Check bucket permissions
   - Ensure IAM policies allow read access

3. **Container Won't Start**
   - Check Docker logs: `docker logs gladly-prod`
   - Verify all dependencies are installed
   - Check port conflicts

4. **Memory Issues**
   - Increase EC2 instance size
   - Monitor memory usage
   - Consider splitting services

### Getting Help
- Check application logs: `docker logs gladly-prod`
- Monitor system resources: `htop` or AWS CloudWatch
- Verify environment variables: `docker exec gladly-prod env`

## Support

For issues specific to this deployment:
1. Check the logs first
2. Verify all environment variables are set
3. Ensure all prerequisites are installed
4. Review the troubleshooting section above

---

**Next Steps after Deployment:**
1. Test all endpoints at `/api/health`
2. Verify conversation data is accessible
3. Test Claude API integration
4. Set up monitoring and alerts
5. Configure backups and disaster recovery
