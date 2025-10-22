# Gladly Conversation Analyzer

A powerful web interface for analyzing customer support conversations using Claude AI, designed for deployment on GitHub, EC2, and cloud storage platforms.

## 🚀 Quick Start

### Prerequisites
- Python 3.11+
- Node.js 18+
- Docker (for containerized deployment)
- Anthropic API key

### 1. Clone and Setup
```bash
git clone https://github.com/YOUR_USERNAME/gladly-conversation-analyzer.git
cd gladly-conversation-analyzer

# Copy environment template
cp env.example .env
```

### 2. Configure Environment
Edit `.env` with your API keys:
```bash
ANTHROPIC_API_KEY=your-anthropic-api-key-here
S3_BUCKET_NAME=your-conversation-bucket (if using S3)
```

### 3. Deploy

**On Linux/Mac:**
```bash
# Production deployment
./deploy.sh production

# Development
./deploy.sh development
```

**On Windows:**
```cmd
# Production deployment
.\deploy.bat production

# Development
.\deploy.bat development
```

**Alternative (Windows PowerShell with Git Bash):**
```bash
# If you have Git Bash installed, you can use the .sh script
bash deploy.sh production
bash deploy.sh development
```

## 🏗️ Architecture

- **Frontend**: React.js with Tailwind CSS
- **Backend**: Flask API with Python 3.11
- **AI**: Claude 3.5 Sonnet via Anthropic API
- **Storage**: S3, Azure Blob, or local files
- **Deployment**: Docker containers

## 📁 Project Structure

```
gladly/
├── src/                    # React frontend
│   ├── components/         # React components
│   └── App.js             # Main app component
├── backend/               # Flask backend
│   ├── api/               # API routes
│   ├── services/          # Business logic
│   └── models/            # Data models
├── public/                # Static assets
├── docker-compose.yml     # Container orchestration
├── Dockerfile            # Container definition
└── deploy.sh             # Deployment script
```

## 🛠️ Development Setup

### Python Environment
```bash
# Create virtual environment
python -m venv venv

# Activate virtual environment
# On Linux/Mac:
source venv/bin/activate
# On Windows:
venv\Scripts\activate

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

**Option 1: Using the deployment script**

**On Linux/Mac:**
```bash
chmod +x deploy.sh
./deploy.sh development
```

**On Windows:**
```cmd
.\deploy.bat development
```

**Option 2: Manual startup**

**Terminal 1 (Backend):**
```bash
# On Linux/Mac:
source venv/bin/activate && python app.py

# On Windows:
venv\Scripts\activate && python app.py
```

**Terminal 2 (Frontend - if developing):**
```bash
npm start
```

## 🎯 Usage Modes

The application supports three main interaction modes:

### 1. Claude Chat
Direct interaction with Claude AI for general questions and tasks.

### 2. Search Data
Search through conversation data using keyword queries.

### 3. Ask Claude (RAG) - **Default Mode**
RAG-powered analysis where Claude plans, retrieves, and analyzes conversation data to answer complex questions.

## 🌐 Deployment Options

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

**On Linux/Mac:**
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
```

**On Windows:**
```cmd
# Clone your repository
git clone https://github.com/YOUR_USERNAME/gladly-conversation-analyzer.git
cd gladly-conversation-analyzer

# Build and deploy
set ANTHROPIC_API_KEY=your-api-key
set S3_BUCKET_NAME=your-bucket-name
set AWS_ACCESS_KEY_ID=your-access-key
set AWS_SECRET_ACCESS_KEY=your-secret-key
.\deploy.bat production
```

### Option B: Docker Containers

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

### Option C: S3 Static Hosting + Lambda

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

## 🔧 CLI Usage

The application also includes a command-line interface for direct interaction:

### Basic Claude API Usage
```bash
# Basic usage (default mode)
python3 claude_api_client.py "Hello, Claude!"

# With custom model
python3 claude_api_client.py "Explain quantum computing" --model claude-3-5-sonnet-20241022

# With system prompt
python3 claude_api_client.py "Write a poem" --system "You are a creative poet who writes in haiku format"

# Streaming response
python3 claude_api_client.py "Tell me a long story" --stream
```

### Conversation Analysis
```bash
# Get summary of conversation data
python3 claude_api_client.py conversations summary

# Search conversations
python3 claude_api_client.py conversations search --query "refund"

# Get specific conversation
python3 claude_api_client.py conversations conversation --conversation-id "vhGOxHmTRtmKJg1Ik0lpYQ"
```

### RAG System
```bash
# Ask Claude about your conversation data
python3 claude_api_client.py ask "What are the main customer complaints?"

# Ask about specific topics
python3 claude_api_client.py ask "What quality issues do customers mention?"
python3 claude_api_client.py ask "How many refund requests were there?"
```

## 🔒 Environment Configuration

### Required Environment Variables
```bash
# Required
ANTHROPIC_API_KEY=your-actual-key-here

# For S3 deployment
S3_BUCKET_NAME=your-actual-bucket-name
AWS_ACCESS_KEY_ID=your-access-key
AWS_SECRET_ACCESS_KEY=your-secret-key

# Optional
FLASK_ENV=development
FLASK_DEBUG=True
```

## 🚨 Troubleshooting

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

## 📊 Production Considerations

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

## 🧪 Testing

Run the test suite to verify functionality:
```bash
python3 test_commands.py
```

## 📝 API Endpoints

- `GET /api/health` - Health check
- `POST /api/claude/chat` - Claude chat
- `POST /api/conversations/search` - Search conversations
- `POST /api/conversations/ask` - RAG analysis

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 📚 Additional Documentation

Historical documentation files have been moved to the `docs/` folder for reference:
- `docs/README_GITHUB.md` - Original GitHub-focused README
- `docs/README_claude_api.md` - Detailed CLI usage documentation
- `docs/QUICK_START.md` - Original quick setup guide
- `docs/AWS_DEPLOYMENT.md` - AWS-specific deployment instructions
- `docs/DEPLOYMENT.md` - Detailed deployment guide

## 🆘 Support

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
