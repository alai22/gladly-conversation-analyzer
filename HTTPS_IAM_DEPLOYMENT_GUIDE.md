# HTTPS Deployment Guide with IAM Role

This guide will help you deploy HTTPS using your existing IAM role `GladlyS3FA` instead of public S3 access.

## Prerequisites

1. **IAM Role Setup**: You should have an IAM role named `GladlyS3FA` with S3 permissions
2. **Environment Variables**: Set these in your system environment or deployment script:
   - `ANTHROPIC_API_KEY` (you already have this)
   - `GLADLY_API_KEY`
   - `GLADLY_AGENT_EMAIL`
   - `S3_BUCKET_NAME`

## Key Changes Made

### 1. Terraform Configuration Updated
- **Removed**: Creation of new IAM role and policies
- **Added**: Reference to existing IAM role `GladlyS3FA`
- **Added**: HTTPS support with SSL certificate
- **Added**: HTTP to HTTPS redirect

### 2. Security Improvements
- **No more public S3 access** - Using IAM role instead
- **HTTPS encryption** - All traffic encrypted
- **Automatic HTTP redirect** - Forces secure connections

## Deployment Steps

### Step 1: Verify IAM Role
Make sure your IAM role `GladlyS3FA` has these permissions:

```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "s3:GetObject",
                "s3:PutObject",
                "s3:DeleteObject",
                "s3:ListBucket"
            ],
            "Resource": [
                "arn:aws:s3:::your-bucket-name",
                "arn:aws:s3:::your-bucket-name/*"
            ]
        }
    ]
}
```

### Step 2: Set Environment Variables
Set these environment variables before running the deployment:

```bash
# Required variables
export ANTHROPIC_API_KEY="your-anthropic-api-key-here"
export GLADLY_API_KEY="your-gladly-api-key"
export GLADLY_AGENT_EMAIL="your.email@company.com"
export S3_BUCKET_NAME="your-s3-bucket-name"

# Optional variables
export AWS_REGION="us-east-1"
```

### Step 3: Deploy Infrastructure and Application

**On Linux/macOS:**
```bash
./deploy_https_iam.sh
```

**On Windows:**
```cmd
deploy_https_iam.bat
```

### Step 4: Verify Deployment

After deployment, test these endpoints:

1. **HTTPS Access**: `https://your-load-balancer-dns-name.elb.amazonaws.com`
2. **HTTP Redirect**: `http://your-load-balancer-dns-name.elb.amazonaws.com` (should redirect to HTTPS)
3. **S3 Access**: The application should now use IAM role instead of public access

## What Happens During Deployment

1. **Infrastructure Update**:
   - Updates Terraform configuration to use existing IAM role
   - Adds HTTPS listener to load balancer
   - Creates SSL certificate (AWS managed)
   - Sets up HTTP to HTTPS redirect

2. **Application Deployment**:
   - Builds Docker image with latest code
   - Deploys container with IAM role attached
   - Removes dependency on AWS credentials in environment

3. **Security Improvements**:
   - All traffic encrypted with HTTPS
   - S3 access through IAM role (no public access)
   - Automatic certificate renewal

## Troubleshooting

### Common Issues

1. **IAM Role Not Found**:
   ```
   Error: IAM role 'GladlyS3FA' not found
   ```
   **Solution**: Create the IAM role with proper S3 permissions

2. **S3 Access Denied**:
   ```
   Error: Access denied to S3 bucket
   ```
   **Solution**: Verify IAM role has correct S3 permissions

3. **HTTPS Not Working**:
   ```
   Error: Certificate validation failed
   ```
   **Solution**: Wait 5-10 minutes for certificate validation

### Useful Commands

```bash
# Check IAM role
aws iam get-role --role-name GladlyS3FA

# Check S3 permissions
aws s3 ls s3://your-bucket-name

# Test HTTPS
curl -I https://your-load-balancer-dns-name.elb.amazonaws.com

# Check application logs
docker logs gladly-prod

# Test S3 access from container
docker exec gladly-prod aws s3 ls s3://your-bucket-name
```

## Benefits of This Setup

1. **Enhanced Security**:
   - No AWS credentials in environment variables
   - S3 access through IAM role only
   - HTTPS encryption for all traffic

2. **Simplified Management**:
   - No need to manage AWS credentials
   - Automatic certificate renewal
   - Centralized IAM permissions

3. **Better Performance**:
   - SSL termination at load balancer
   - HTTP to HTTPS redirect
   - Optimized security groups

## Next Steps

After successful deployment:

1. **Update Application URLs**: Change any hardcoded HTTP URLs to HTTPS
2. **Test All Features**: Verify S3 access and HTTPS functionality
3. **Monitor Performance**: Check CloudWatch logs for any issues
4. **Update Documentation**: Update any documentation with new HTTPS URLs

Your application will now be accessible via HTTPS and use secure IAM role-based S3 access!
