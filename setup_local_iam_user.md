# Setting Up IAM User for Local Development

## Situation

You have an IAM **role** (`GladlyS3FA`) that works on EC2, but you need an IAM **user** with access keys for local development.

## Solution: Create an IAM User

### Step 1: Create New IAM User in AWS Console

1. Go to AWS Console → IAM → Users
2. Click "Create user"
3. Name it: `gladly-local-dev` (or similar)
4. ✅ Check "Provide user access to the AWS Management Console" (optional, for testing)
5. Click Next

### Step 2: Attach S3 Permissions

You have two options:

#### Option A: Attach the Same Policy as the Role

1. Find the `GladlyS3FA` role: IAM → Roles → `GladlyS3FA`
2. Click on the role → "Permissions" tab
3. Note which policies are attached (likely an inline policy or managed policy)
4. When creating the user, attach the same policy/policies

#### Option B: Create Custom Policy for the User

1. IAM → Policies → Create policy
2. Use JSON editor and paste this (adjust bucket name if needed):

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "s3:GetObject",
        "s3:PutObject",
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

3. Name it: `GladlyS3LocalDevPolicy`
4. Attach this policy to your new user

### Step 3: Create Access Keys

1. Go to your new user: IAM → Users → `gladly-local-dev`
2. Click "Security credentials" tab
3. Scroll to "Access keys"
4. Click "Create access key"
5. Choose use case: "Application running outside AWS"
6. Click "Create access key"
7. **IMPORTANT:** Copy both:
   - Access key ID
   - Secret access key (you won't see it again!)

### Step 4: Configure Locally

Now set up the credentials:

#### Option A: Update AWS CLI Config

```bash
aws configure
```

Enter:
- AWS Access Key ID: [from Step 3]
- AWS Secret Access Key: [from Step 3]
- Default region: us-east-2
- Default output format: json

#### Option B: Add to `.env` File

Add to your `.env` file:

```bash
AWS_ACCESS_KEY_ID=your-access-key-id-from-step-3
AWS_SECRET_ACCESS_KEY=your-secret-access-key-from-step-3
```

### Step 5: Test

```bash
# Test your identity
aws sts get-caller-identity

# Test S3 access
aws s3 ls s3://gladly-conversations-alai22/

# If both work, restart Flask!
```

## Alternative: Use Role Assumption (Advanced)

If you want to assume the role from local development:

1. You need an IAM user with permission to assume the role
2. Then use AWS STS to get temporary credentials
3. More complex, but uses the same role

For simplicity, creating a dedicated user for local dev is recommended.

## Security Best Practices

- ✅ Use minimal permissions (only S3 access to specific bucket)
- ✅ Don't commit access keys to git (`.env` is in `.gitignore`)
- ✅ Rotate keys periodically
- ✅ Consider using different keys for different environments

## Troubleshooting

**Still getting InvalidAccessKeyId?**
- Double-check you copied the keys correctly (no extra spaces)
- Make sure the user has the S3 permissions attached
- Verify the bucket name in the policy matches: `gladly-conversations-alai22`

**Access Denied?**
- Check the IAM policy allows the actions you need
- Verify the bucket name in the policy ARN is correct
- Make sure the policy is attached to the user

