# Quick Setup: Create IAM User for Local Development

Since you have an IAM **role** (`GladlyS3FA`) that works on EC2, you need to create an IAM **user** for local development.

## Steps (5 minutes)

### 1. Go to AWS Console → IAM → Users → Create User

- Username: `gladly-local-dev`
- ✅ Check "Provide user access to the AWS Management Console" (optional)
- Click Next

### 2. Set Permissions

**Option A (Recommended):** Copy permissions from the role
1. Go to IAM → Roles → `GladlyS3FA`
2. Click "Permissions" tab
3. Note which policies/permissions it has
4. Attach the same policies to your new user

**Option B:** Attach this policy (based on your role setup):

When creating the user:
- Choose "Attach policies directly"
- Click "Create policy"
- Use JSON tab, paste:

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
        "s3:ListBucket",
        "s3:HeadBucket"
      ],
      "Resource": [
        "arn:aws:s3:::gladly-conversations-alai22",
        "arn:aws:s3:::gladly-conversations-alai22/*"
      ]
    }
  ]
}
```

- Name: `GladlyS3LocalDevPolicy`
- Click Create Policy
- Refresh, then attach it to your user

### 3. Create Access Keys

1. Go to your user: IAM → Users → `gladly-local-dev`
2. "Security credentials" tab
3. "Access keys" section → "Create access key"
4. Use case: "Application running outside AWS"
5. Click "Create access key"
6. **SAVE BOTH:**
   - Access key ID
   - Secret access key (shown only once!)

### 4. Configure Locally

**Option A: Update AWS CLI**
```bash
aws configure
```
Enter your new access key ID and secret.

**Option B: Add to `.env` file**
Add to your `.env`:
```bash
AWS_ACCESS_KEY_ID=AKIA...your-key-here
AWS_SECRET_ACCESS_KEY=...your-secret-here
```

### 5. Test

```bash
aws sts get-caller-identity
aws s3 ls s3://gladly-conversations-alai22/
```

Both should work! Then restart Flask.

## Quick Reference

**What you need:**
- ✅ IAM User (for local dev)
- ✅ Access keys (to authenticate)
- ✅ Same S3 permissions as `GladlyS3FA` role

**Why:**
- EC2 uses IAM roles (automatic, no keys)
- Local dev needs access keys (can't use roles directly)

See `setup_local_iam_user.md` for detailed instructions.

