# Terraform Cleanup Guide

Since we're using the simpler nginx approach instead of Terraform, you should clean up any Terraform-created resources.

## 🔍 What Terraform Created

Based on the `terraform apply` that ran, these resources were created:

- ✅ **VPC** (Virtual Private Cloud) - `gladly-prod-vpc`
- ✅ **Subnets** - Two public subnets in different availability zones
- ✅ **Internet Gateway** - For internet connectivity
- ✅ **Route Tables** - For routing traffic
- ✅ **Security Groups** - Firewall rules
- ✅ **Application Load Balancer** - `gladly-prod-alb` (may be partially created)
- ✅ **Target Groups** - For load balancer
- ✅ **S3 Bucket** - `gladly-prod-conversations-*`
- ✅ **Key Pair** - `gladly-prod-key-pair`
- ✅ **IAM Instance Profile** - (may have failed due to permissions)

## 🧹 Option 1: Automatic Cleanup (Recommended)

Use the cleanup script:

```bash
# On your EC2 instance
git pull origin main
chmod +x cleanup_terraform.sh
./cleanup_terraform.sh
```

This will:
1. Show you what will be deleted
2. Ask for confirmation
3. Destroy all Terraform resources
4. Optionally remove state files

## 🧹 Option 2: Manual Cleanup

If you prefer to do it manually:

```bash
# On your EC2 instance
cd terraform

# See what will be destroyed
terraform plan -destroy

# Destroy everything
terraform destroy
```

## 🧹 Option 3: Keep Some Resources

If you want to keep the S3 bucket (since you're using S3 for conversation data):

1. **Before running cleanup**, go to AWS Console → S3
2. **Find the bucket** `gladly-prod-conversations-*`
3. **Note the exact name** or make it non-terraform managed
4. **Remove it from Terraform state**:
   ```bash
   terraform state rm aws_s3_bucket.conversation_data
   terraform state rm aws_s3_bucket_versioning.conversation_data_versioning
   ```
5. **Then run cleanup** for everything else

## 📋 What to Keep

You should **keep**:
- ✅ Your existing EC2 instance (not created by Terraform)
- ✅ Your Docker container (runs independently)
- ✅ Your `.env` file
- ✅ Your IAM role `GladlyS3FA` (used by your instance)

You should **delete**:
- ❌ Terraform-created VPC, subnets, load balancer
- ❌ Terraform-created security groups
- ❌ Terraform state files (optional, but recommended)

## ⚠️ Important Notes

1. **Your Docker container will continue running** - Terraform cleanup won't affect it
2. **Your current IP access** - Will continue working after cleanup
3. **Nginx setup** - Can run alongside cleanup (doesn't conflict)

## 🚀 After Cleanup

Once cleanup is complete:

1. **Set up nginx** (if you haven't already):
   ```bash
   sudo ./setup_https_nginx.sh
   ```

2. **Verify your app works**:
   ```bash
   # Check Docker
   docker ps
   
   # Check nginx
   sudo systemctl status nginx
   ```

3. **Test HTTPS**:
   ```bash
   curl -k https://localhost
   ```

## 💡 Why Clean Up?

- **Avoids AWS costs** - Load balancers and unused resources cost money
- **Avoids confusion** - No leftover infrastructure
- **Cleaner setup** - nginx doesn't need Terraform resources

## 📝 State Files

After cleanup, you can optionally remove:
- `terraform/.terraform/` - Provider plugins
- `terraform/terraform.tfstate` - State file
- `terraform/terraform.tfvars` - Variable values

But you can keep the `terraform/` directory if you want - it won't interfere with nginx.
