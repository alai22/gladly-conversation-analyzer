# Fixing InvalidAccessKeyId Error

## The Problem

Your AWS credentials are configured (showing in `aws configure list`), but they're invalid for accessing the S3 bucket. This typically means:

1. **Credentials are from a different AWS account** than where the bucket exists
2. **Access keys have been rotated/deleted** 
3. **Access keys are incorrect** in your credentials file

## Solution Steps

### Step 1: Identify Which AWS Account Owns the Bucket

The bucket `gladly-conversations-alai22` is in a specific AWS account. You need to know which account that is.

**If you created the bucket:**
- Check which AWS account you were logged into when creating it
- Or check the bucket's permissions/owner in AWS Console

**If someone else created it:**
- Ask them which AWS account it's in
- You'll need credentials from that account (or cross-account access)

### Step 2: Check Your Current AWS Account

```bash
aws sts get-caller-identity
```

This shows which AWS account your credentials are for. If it doesn't match the bucket's account, that's the problem.

### Step 3: Get Correct Credentials

#### Option A: If You Have Access to the Correct AWS Account

1. Log into AWS Console with the account that owns the bucket
2. Go to IAM → Users → (your user)
3. Security credentials tab
4. Create new access key (or use existing one)
5. Update your AWS credentials:

   ```bash
   aws configure
   ```
   
   Enter the new:
   - AWS Access Key ID
   - AWS Secret Access Key  
   - Default region: us-east-2

#### Option B: If You Need Cross-Account Access

The bucket owner needs to add a bucket policy allowing your AWS account access, or give you credentials from their account.

#### Option C: If Working on EC2

On EC2, you're using IAM roles (not access keys). For local dev, you need to either:
1. Get credentials that match the bucket's account
2. Or set up cross-account access

### Step 4: Verify Credentials Work

After updating credentials:

```bash
# Check your identity
aws sts get-caller-identity

# Try listing the bucket again
aws s3 ls s3://gladly-conversations-alai22/
```

If this works, your Flask app will work too!

## Quick Fix: Update Credentials

If you know the correct AWS account:

1. **Get new access keys** from AWS Console (IAM → Users → Your User → Security Credentials)

2. **Update credentials:**
   ```bash
   aws configure
   ```

3. **Or set in .env file** (if using environment variables):
   ```bash
   AWS_ACCESS_KEY_ID=your-new-access-key-id
   AWS_SECRET_ACCESS_KEY=your-new-secret-access-key
   ```

## Common Scenarios

### Scenario 1: Personal AWS Account vs Work AWS Account
- Bucket is in work account, credentials are for personal account
- **Fix:** Use credentials from the work account

### Scenario 2: Multiple AWS Accounts
- Bucket in Account A, credentials for Account B  
- **Fix:** Get credentials for Account A or set up cross-account access

### Scenario 3: Credentials Were Rotated
- Old credentials deleted, new ones created
- **Fix:** Update with new access keys

## Testing After Fix

Once credentials are correct, restart Flask and you should see:
```
✅ Loaded conversations from S3
```

Instead of:
```
❌ InvalidAccessKeyId
```

