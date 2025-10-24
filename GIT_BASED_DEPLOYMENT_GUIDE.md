# HTTPS Deployment Guide - Git-Based Workflow

This guide explains how to set up HTTPS with your existing **Git-based deployment workflow**.

## 🔄 Your Current Workflow

1. **Develop locally** → Push to GitHub
2. **On EC2** → Pull from GitHub → Deploy with `deploy.sh`

## 🚀 Updated Two-Step Process

### Step 1: One-Time Infrastructure Setup (On EC2)
**Run once** on your EC2 instance to set up HTTPS infrastructure:
```bash
./setup_https_infrastructure.sh
```

### Step 2: Regular Git-Based Deployments
**Your existing workflow** - push to GitHub, then on EC2:
```bash
git pull origin main
./deploy.sh production
```

## 📋 What Each Script Does

### `setup_https_infrastructure.sh` (One-time on EC2)
- ✅ Sets up HTTPS infrastructure with Terraform
- ✅ Configures load balancer with SSL certificate
- ✅ Sets up HTTP to HTTPS redirect
- ✅ Uses your existing IAM role `GladlyS3FA`
- ✅ **Does NOT deploy the application**

### `deploy.sh production` (Regular deployments on EC2)
- ✅ Builds Docker image
- ✅ **Loads environment variables from `.env` file**
- ✅ Deploys application container
- ✅ Uses IAM role for S3 access (no AWS credentials needed)
- ✅ **Works with your existing Git workflow**

## 🎯 Your Complete Workflow

### Initial Setup (Run Once on EC2)
1. **Pull latest code from GitHub**:
   ```bash
   git pull origin main
   ```

2. **Set up HTTPS infrastructure**:
   ```bash
   ./setup_https_infrastructure.sh
   ```

3. **Deploy application**:
   ```bash
   ./deploy.sh production
   ```

### Regular Deployments (Your Normal Process)
1. **Develop locally** → Make changes
2. **Push to GitHub**:
   ```bash
   git add .
   git commit -m "Your changes"
   git push origin main
   ```

3. **On EC2** → Pull and deploy:
   ```bash
   git pull origin main
   ./deploy.sh production
   ```

## 🔧 Key Changes Made

### Updated `deploy.sh`
- ✅ **Loads `.env` file** automatically
- ✅ **Removed AWS credentials** (using IAM role)
- ✅ **Stops existing container** before deploying new one
- ✅ **Works with your existing Git workflow**

### New `setup_https_infrastructure.sh`
- ✅ **One-time infrastructure setup**
- ✅ **Uses existing IAM role**
- ✅ **Sets up HTTPS with SSL certificate**
- ✅ **Does NOT interfere with your Git workflow**

## 📁 File Structure

```
your-project/
├── .env                          # Your environment variables (on EC2)
├── deploy.sh                     # Your existing deployment script (updated)
├── setup_https_infrastructure.sh # New: One-time infrastructure setup
├── terraform/
│   └── main.tf                   # Updated to use IAM role
└── ...
```

## 🚀 Complete Deployment Process

### First Time Setup (On EC2)
```bash
# 1. Pull latest code
git pull origin main

# 2. Set up HTTPS infrastructure (one-time)
./setup_https_infrastructure.sh

# 3. Deploy application
./deploy.sh production
```

### Regular Deployments (Your Normal Process)
```bash
# 1. Develop locally → Push to GitHub
git add .
git commit -m "Your changes"
git push origin main

# 2. On EC2 → Pull and deploy
git pull origin main
./deploy.sh production
```

## 💡 Benefits of This Approach

1. **Keeps Your Git Workflow**:
   - Push to GitHub (local)
   - Pull from GitHub (EC2)
   - Deploy with `deploy.sh`

2. **Separation of Concerns**:
   - Infrastructure setup (one-time)
   - Application deployment (regular)

3. **Security**:
   - HTTPS encryption
   - IAM role for S3 access
   - No AWS credentials in environment

4. **Flexibility**:
   - Deploy application anytime
   - Infrastructure changes only when needed
   - Easy to maintain

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

## 🎯 Summary

- **`setup_https_infrastructure.sh`** = One-time HTTPS infrastructure setup (on EC2)
- **`deploy.sh production`** = Regular application deployments (your existing workflow)
- **Git workflow** = Push to GitHub (local) → Pull from GitHub (EC2) → Deploy
- **`.env` file** = Your environment variables (on EC2, no AWS credentials needed)

This approach gives you HTTPS security while keeping your existing Git-based deployment workflow intact!

## 📝 Quick Reference

### Initial Setup (On EC2)
```bash
git pull origin main
./setup_https_infrastructure.sh
./deploy.sh production
```

### Regular Deployments
```bash
# Local development
git add .
git commit -m "Your changes"
git push origin main

# On EC2
git pull origin main
./deploy.sh production
```

This maintains your Git workflow while adding HTTPS security!
