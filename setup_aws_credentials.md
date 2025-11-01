# Setting Up AWS Credentials for Local Development

## The Problem

You're getting `InvalidAccessKeyId` errors because AWS credentials aren't configured for local development. On EC2, your app uses IAM roles (no credentials needed), but locally you need explicit credentials.

## Solution: Add AWS Credentials to `.env`

### Option 1: Use Your Existing AWS Credentials

If you have AWS credentials that can access the S3 bucket `gladly-conversations-alai22`, add them to your `.env` file:

```bash
# AWS Credentials (add these to your .env file)
AWS_ACCESS_KEY_ID=your-actual-access-key-id-here
AWS_SECRET_ACCESS_KEY=your-actual-secret-access-key-here

# S3 Configuration (verify these are correct)
STORAGE_TYPE=s3
S3_BUCKET_NAME=gladly-conversations-alai22
S3_FILE_KEY=conversation_items.jsonl
S3_REGION=us-east-2
```

### Option 2: Use AWS CLI Credentials

If you've configured AWS CLI with `aws configure`, boto3 will automatically use those credentials. Just make sure:

```bash
# Verify AWS CLI is configured
aws configure list

# Test S3 access
aws s3 ls s3://gladly-conversations-alai22/
```

If this works, you don't need to set `AWS_ACCESS_KEY_ID` and `AWS_SECRET_ACCESS_KEY` in `.env`.

### Option 3: Create a New IAM User for Local Dev

1. Go to AWS Console → IAM → Users
2. Create a new user (e.g., `gladly-local-dev`)
3. Attach a policy with S3 read access:
   ```json
   {
     "Version": "2012-10-17",
     "Statement": [
       {
         "Effect": "Allow",
         "Action": [
           "s3:GetObject",
           "s3:ListBucket"
         ],
         "Resource": [
           "arn:aws:s3:::gladly-conversations-alai22",
           "arn:aws:s3:::gladly-conversations-alai22/*"
         ]
       }
     ]
   }
   ```
4. Create access keys for this user
5. Add the keys to your `.env` file

## Finding Your Credentials

### If You Don't Remember Your Credentials

1. **Check if AWS CLI is configured:**
   ```bash
   aws configure list
   ```

2. **Check your EC2 instance** (if you have access):
   - The EC2 instance uses IAM roles, not credentials
   - But you might have credentials stored elsewhere

3. **Create new credentials:**
   - Create a new IAM user as described above
   - This is the safest approach for local dev

## Verifying Setup

After adding credentials to `.env`, restart your Flask server. You should see:

```
✅ S3 storage initialized successfully
✅ Loaded conversations from S3
```

Instead of:
```
❌ InvalidAccessKeyId
```

## Security Note

- The `.env` file should be in `.gitignore` (don't commit credentials)
- Never share your AWS credentials
- Use IAM users with minimal permissions for local dev

## Quick Test

After setting credentials, test with:

```bash
python -c "import boto3; s3 = boto3.client('s3', region_name='us-east-2'); print(s3.head_bucket(Bucket='gladly-conversations-alai22'))"
```

If this works, your credentials are correct!

