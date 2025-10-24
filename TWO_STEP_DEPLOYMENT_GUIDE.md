# HTTPS Deployment Guide - Two-Step Process

This guide explains how to set up HTTPS with your existing workflow using `.env` files.

## 🔄 Two-Step Process

### Step 1: One-Time Infrastructure Setup
**Run once** to set up HTTPS infrastructure:
```bash
./setup_https_infrastructure.sh
```

### Step 2: Regular Application Deployments
**Run whenever** you want to deploy your application:
```bash
./deploy.sh production
```

## 📋 What Each Script Does

### `setup_https_infrastructure.sh` (One-time)
- ✅ Sets up HTTPS infrastructure with Terraform
- ✅ Configures load balancer with SSL certificate
- ✅ Sets up HTTP to HTTPS redirect
- ✅ Uses your existing IAM role `GladlyS3FA`
- ✅ **Does NOT deploy the application**

### `deploy.sh production` (Regular deployments)
- ✅ Builds Docker image
- ✅ Loads environment variables from `.env` file
- ✅ Deploys application container
- ✅ Uses IAM role for S3 access (no AWS credentials needed)
- ✅ **Works with your existing workflow**

## 🎯 Your Workflow

### Initial Setup (Run Once)
1. **Set up HTTPS infrastructure**:
   ```bash
   ./setup_https_infrastructure.sh
   ```

2. **Create `.env` file on EC2**:
   ```bash
   # On your EC2 instance
   cat > .env << EOF
   ANTHROPIC_API_KEY=your-anthropic-api-key-here
   GLADLY_API_KEY=your-gladly-api-key
   GLADLY_AGENT_EMAIL=your.email@company.com
   S3_BUCKET_NAME=your-s3-bucket-name
   AWS_DEFAULT_REGION=us-east-1
   EOF
   ```

### Regular Deployments (Run Anytime)
```bash
# On your EC2 instance
./deploy.sh production
```

## 🔧 Key Changes Made

### Updated `deploy.sh`
- ✅ **Loads `.env` file** automatically
- ✅ **Removed AWS credentials** (using IAM role)
- ✅ **Stops existing container** before deploying new one
- ✅ **Works with your existing workflow**

### New `setup_https_infrastructure.sh`
- ✅ **One-time infrastructure setup**
- ✅ **Uses existing IAM role**
- ✅ **Sets up HTTPS with SSL certificate**
- ✅ **Does NOT interfere with your deploy.sh**

## 📁 File Structure

```
your-project/
├── .env                          # Your environment variables
├── deploy.sh                     # Your existing deployment script (updated)
├── setup_https_infrastructure.sh # New: One-time infrastructure setup
├── terraform/
│   └── main.tf                   # Updated to use IAM role
└── ...
```

## 🚀 Deployment Process

### First Time (Infrastructure Setup)
```bash
# 1. Set up HTTPS infrastructure (one-time)
./setup_https_infrastructure.sh

# 2. Create .env file on EC2
# 3. Deploy application
./deploy.sh production
```

### Regular Deployments
```bash
# Just deploy the application (infrastructure already set up)
./deploy.sh production
```

## 🔍 What Happens During Each Step

### Infrastructure Setup (`setup_https_infrastructure.sh`)
1. Checks prerequisites (AWS CLI, Terraform, Docker)
2. Verifies IAM role `GladlyS3FA` exists
3. Creates Terraform configuration
4. Deploys HTTPS infrastructure
5. **Stops here** - doesn't deploy application

### Application Deployment (`deploy.sh production`)
1. Loads environment variables from `.env`
2. Builds Docker image
3. Stops existing container
4. Deploys new container with IAM role
5. **Application is now running with HTTPS**

## 💡 Benefits of This Approach

1. **Separation of Concerns**:
   - Infrastructure setup (one-time)
   - Application deployment (regular)

2. **Works with Your Workflow**:
   - Uses your existing `deploy.sh`
   - Works with your `.env` file
   - No changes to your regular process

3. **Security**:
   - HTTPS encryption
   - IAM role for S3 access
   - No AWS credentials in environment

4. **Flexibility**:
   - Deploy application anytime
   - Infrastructure changes only when needed
   - Easy to maintain

## 🎯 Summary

- **`setup_https_infrastructure.sh`** = One-time HTTPS infrastructure setup
- **`deploy.sh production`** = Regular application deployments (your existing workflow)
- **`.env` file** = Your environment variables (no AWS credentials needed)

This approach gives you HTTPS security while keeping your existing deployment workflow intact!
