# AWS Deployment Guide for Gladly Conversation Analyzer

## 🚀 Quick AWS Deployment Steps

### Prerequisites ✅
- AWS account access (provided by IT)
- GitHub account
- Your Anthropic API key

## 📋 Step-by-Step Deployment

### Step 1: Push to GitHub
```bash
# Create repository on GitHub first, then:
git remote add origin https://github.com/YOUR_USERNAME/gladly-conversation-analyzer.git
git branch -M main
git push -u origin main
```

### Step 2: Launch EC2 Instance

**Via AWS Console:**
1. Go to **EC2 Dashboard** → **Launch Instance**
2. **AMI**: Amazon Linux 2023 (free tier eligible)
3. **Instance Type**: t3.medium (recommended for AI processing)
4. **Key Pair**: Create new or use existing
5. **Security Group**: Allow HTTP (80), HTTPS (443), SSH (22)
6. **Storage**: 20GB minimum

**Via Terraform (Automated):**
```bash
cd terraform/
terraform init
terraform plan
terraform apply
```

### Step 3: Connect to EC2
```bash
# Download your key pair (.pem file) from AWS Console
chmod 400 your-key.pem
ssh -i your-key.pem ec2-user@YOUR_EC2_PUBLIC_IP

# Note: IP address changes when you stop/start the instance
# Check AWS Console for current public IP
```

### Step 4: Deploy Application on EC2

**Option A: Direct Docker Deployment**
```bash
# On EC2 instance:
sudo yum update -y
sudo yum install docker git -y
sudo service docker start
sudo usermod -a -G docker ec2-user

# Log out and back in
exit
ssh -i your-key.pem ec2-user@YOUR_EC2_PUBLIC_IP

# Clone your repository
git clone https://github.com/YOUR_USERNAME/gladly-conversation-analyzer.git
cd gladly-conversation-analyzer

# Set environment variables
export ANTHROPIC_API_KEY="your-anthropic-api-key"
export S3_BUCKET_NAME="your-conversation-bucket"  # Optional
export AWS_ACCESS_KEY_ID="your-access-key"        # Optional
export AWS_SECRET_ACCESS_KEY="your-secret-key"    # Optional

# Deploy
chmod +x deploy.sh
./deploy.sh production
```

**Note: After instance restart, you need to redeploy:**
```bash
# Set environment variables again
export ANTHROPIC_API_KEY="your-anthropic-api-key"
export S3_BUCKET_NAME="your-conversation-bucket"
export AWS_DEFAULT_REGION="us-east-1"

# Redeploy
./deploy.sh production
```

**Option B: Using Docker Compose**
```bash
# On EC2 instance:
export ANTHROPIC_API_KEY="your-key"
export S3_BUCKET_NAME="your-bucket"
docker-compose up -d
```

### Step 5: Set Up S3 for Conversation Data (Optional)

**Create S3 Bucket:**
1. Go to **S3 Console** → **Create Bucket**
2. **Bucket Name**: `gladly-conversations-YOUR_NAME`
3. **Region**: Same as EC2 (us-east-1 recommended)
4. **Upload**: Your `conversation_items.jsonl` file

**Configure IAM Permissions:**
1. Go to **IAM Console** → **Roles**
2. Find your EC2 instance role
3. **Attach Policy**: `AmazonS3ReadOnlyAccess`

### Step 6: Configure Domain & SSL (Optional)

**Route 53 (if you have a domain):**
1. **Route 53** → **Hosted Zones**
2. **Create Record**: Point domain to EC2 public IP
3. **SSL Certificate**: Use AWS Certificate Manager

## 🔧 Environment Variables Setup

Create a `.env` file on EC2:
```bash
# Required
ANTHROPIC_API_KEY=your-anthropic-api-key-here

# Optional (for S3 storage)
S3_BUCKET_NAME=your-conversation-bucket
AWS_ACCESS_KEY_ID=your-access-key
AWS_SECRET_ACCESS_KEY=your-secret-key

# Flask Configuration
FLASK_ENV=production
PORT=5000
HOST=0.0.0.0
```

## 🚀 Alternative: AWS App Runner (Easiest)

**If you prefer a simpler approach:**

1. **App Runner Console** → **Create Service**
2. **Source**: GitHub repository
3. **Build**: Dockerfile (auto-detected)
4. **Environment Variables**: Add your API keys
5. **Deploy**: Automatic deployment

**Benefits:**
- No server management
- Automatic scaling
- Built-in load balancing
- Pay-per-use pricing

## 💰 Cost Estimation

**EC2 t3.medium:**
- ~$30-50/month (depending on usage)
- Free tier eligible for first year

**App Runner:**
- ~$25-40/month (pay-per-use)
- Scales automatically

**S3 Storage:**
- ~$1-5/month (for conversation data)

## 🔒 Security Checklist

- ✅ Environment variables for secrets
- ✅ Security groups configured
- ✅ HTTPS enabled (with SSL certificate)
- ✅ Regular security updates
- ✅ Backup strategy

## 📊 Monitoring Setup

**CloudWatch:**
1. **EC2 Console** → **Monitoring** tab
2. **Enable**: Detailed monitoring
3. **Set up**: Alarms for CPU/Memory usage

**Application Health:**
- Health check endpoint: `/health`
- Monitor API response times
- Set up alerts for downtime

## 🆘 Troubleshooting

**Common Issues:**

1. **Port 5000 not accessible:**
   ```bash
   # Check security group allows port 5000
   # Or use port 80: docker run -p 80:5000
   ```

2. **API key not working:**
   ```bash
   # Verify environment variable is set
   echo $ANTHROPIC_API_KEY
   ```

3. **S3 access denied:**
   ```bash
   # Check IAM permissions
   # Verify bucket name and region
   ```

## 🎯 Next Steps After Deployment

1. **Test**: Visit `http://YOUR_EC2_IP:5000`
2. **Monitor**: Set up CloudWatch alarms
3. **Backup**: Configure automated backups
4. **Scale**: Add more instances if needed
5. **SSL**: Add HTTPS certificate

## 📞 Support

- **AWS Documentation**: https://docs.aws.amazon.com/
- **EC2 Troubleshooting**: AWS Support Center
- **Application Issues**: Check `/var/log/gladly-deploy.log` on EC2

---

**Ready to deploy?** Start with Step 1 (GitHub) and work through each step!

