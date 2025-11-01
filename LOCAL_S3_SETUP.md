# Setting Up S3 for Local Development

## Quick Setup

To use S3 for local development, you need to set the following environment variables:

### Option 1: Create a `.env` file (Recommended)

Create a `.env` file in the project root with:

```bash
# Storage Configuration
STORAGE_TYPE=s3
S3_BUCKET_NAME=your-actual-bucket-name
S3_FILE_KEY=conversation_items.jsonl
S3_REGION=us-east-1

# AWS Credentials
AWS_ACCESS_KEY_ID=your-aws-access-key-id
AWS_SECRET_ACCESS_KEY=your-aws-secret-access-key
```

### Option 2: Use AWS Credentials File

If you have AWS CLI configured, boto3 will automatically use credentials from `~/.aws/credentials`:

```bash
# No need to set AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY
# Just set:
STORAGE_TYPE=s3
S3_BUCKET_NAME=your-actual-bucket-name
S3_FILE_KEY=conversation_items.jsonl
S3_REGION=us-east-1
```

### Option 3: Set Environment Variables in PowerShell

```powershell
$env:STORAGE_TYPE="s3"
$env:S3_BUCKET_NAME="your-actual-bucket-name"
$env:S3_FILE_KEY="conversation_items.jsonl"
$env:S3_REGION="us-east-1"
$env:AWS_ACCESS_KEY_ID="your-aws-access-key-id"
$env:AWS_SECRET_ACCESS_KEY="your-aws-secret-access-key"
```

## Finding Your S3 Bucket Name

If you're using the same bucket as production on EC2, check your EC2 instance:

```bash
# SSH into your EC2 instance
ssh -i your-key.pem ec2-user@your-ec2-ip

# Check environment variables
cat .env | grep S3_BUCKET_NAME
```

Or check your production deployment configuration.

## Verifying Configuration

After setting the environment variables, restart your Flask server. You should see:

```
✅ S3 storage initialized successfully
✅ Loaded conversations from S3
```

If you see errors about "InvalidAccessKeyId", check:
1. AWS credentials are correct
2. S3 bucket name is correct (not the placeholder)
3. IAM user/credentials have permission to access the bucket

## Notes

- The `.env` file is typically in `.gitignore` (don't commit credentials)
- On EC2, IAM roles are used (no credentials needed in .env)
- For local dev, you need explicit AWS credentials

