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
```bash
# Production deployment
./deploy.sh production

# Development
./deploy.sh development
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
├── *.py                   # Flask backend
├── Dockerfile            # Container configuration
├── docker-compose.yml    # Multi-service deployment
├── deploy.sh            # Deployment script
├── env.example          # Environment template
├── DEPLOYMENT.md        # Detailed deployment guide
└── requirements.txt     # Python dependencies
```

## 🔧 Core Features

- **Conversation Analysis**: AI-powered analysis of customer support interactions
- **Semantic Search**: Find relevant conversations quickly
- **Multiple Storage Backends**: S3, Azure Blob, or local file support
- **RESTful API**: Clean API for integration
- **Real-time Streaming**: Claude API streaming responses
- **Conversation Insights**: Comprehensive data summaries and analytics

## 🌐 API Endpoints

- `GET /api/health` - Health check
- `POST /api/claude/chat` - Send message to Claude
- `GET /api/conversations/summary` - Conversation data summary
- `POST /api/conversations/search` - Semantic search
- `POST /api/conversations/ask` - Ask questions about conversations

## 🚀 Deployment Options

### 1. Local Development
```bash
./deploy.sh development
```
Access at: http://localhost:5000

### 2. Production Server (EC2)
```bash
export ANTHROPIC_API_KEY="your-key"
export S3_BUCKET_NAME="your-bucket"
./deploy.sh production
```

### 3. Docker Compose
```bash
docker-compose up -d
```

### 4. Kubernetes (Advanced)
See `DEPLOYMENT.md` for Kubernetes manifests

## 🔒 Security

- Environment variables for all secrets
- Non-root container execution
- Health checks and monitoring
- CORS configuration
- Input validation

## 📊 Production Considerations

- **CPU**: Recommended t3.medium+ for AI processing
- **Memory**: 512MB+ RAM minimum
- **Storage**: 10GB+ for conversation data
- **Security**: Regular updates, HTTPS, firewall rules

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/new-feature`
3. Commit changes: `git commit -am 'Add new feature'`
4. Push to branch: `git push origin feature/new-feature`
5. Submit a Pull Request

## 📝 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🆘 Support

- 📖 Detailed guide: [DEPLOYMENT.md](DEPLOYMENT.md)
- 🐛 Issues: Report bugs via GitHub Issues
- 💡 Features: Suggest enhancements via GitHub Discussions

## 🏆 Features Overview

- ⚡ **Fast**: Optimized for production performance
- 🔒 **Secure**: Environment-based configuration
- 🌐 **Scalable**: Horizontal scaling support
- 📱 **Responsive**: Mobile-friendly interface
- 🔧 **Customizable**: Easily extensible architecture
- 📊 **Analytics**: Rich conversation insights
- 🚀 **Deployment**: Multiple deployment options

---

**Ready to deploy?** Check out the [Deployment Guide](DEPLOYMENT.md) for detailed instructions!
