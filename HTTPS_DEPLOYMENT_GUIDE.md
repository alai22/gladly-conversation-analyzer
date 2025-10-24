# HTTPS Deployment Guide for Gladly Conversation Analyzer

This guide will help you upgrade your EC2 instance from HTTP to HTTPS using AWS Certificate Manager (ACM) and Application Load Balancer.

## Prerequisites

1. **Domain Name (Optional but Recommended)**: You'll need a domain name to get a proper SSL certificate. If you don't have one, you can still use the AWS-provided certificate for the load balancer domain.

2. **AWS CLI Configured**: Make sure your AWS CLI is configured with appropriate permissions.

3. **Terraform Installed**: Ensure Terraform is installed and configured.

## Deployment Options

### Option 1: Using AWS Load Balancer Domain (No Custom Domain)

This is the simplest option and works immediately without needing a domain name.

```bash
# Deploy with default AWS certificate
cd terraform
terraform init
terraform plan
terraform apply
```

After deployment, your application will be available at:
- **HTTPS**: `https://your-load-balancer-dns-name.elb.amazonaws.com`
- **HTTP**: `http://your-load-balancer-dns-name.elb.amazonaws.com` (redirects to HTTPS)

### Option 2: Using Custom Domain with SSL Certificate

If you have a domain name, follow these steps:

1. **Update Terraform Variables**:
   ```bash
   # Create terraform.tfvars file
   cat > terraform/terraform.tfvars << EOF
   domain_name = "your-domain.com"
   environment = "gladly-prod"
   aws_region = "us-east-1"
   EOF
   ```

2. **Deploy Infrastructure**:
   ```bash
   cd terraform
   terraform init
   terraform plan
   terraform apply
   ```

3. **Configure DNS**:
   After deployment, Terraform will output the load balancer DNS name. Create a CNAME record in your domain's DNS settings:
   ```
   Type: CNAME
   Name: @ (or your subdomain)
   Value: your-load-balancer-dns-name.elb.amazonaws.com
   ```

4. **Wait for Certificate Validation**:
   The SSL certificate will be automatically validated via DNS. This usually takes 5-10 minutes.

### Option 3: Using Existing SSL Certificate

If you already have an SSL certificate in AWS Certificate Manager:

1. **Get Certificate ARN**:
   ```bash
   aws acm list-certificates --region us-east-1
   ```

2. **Update Terraform Variables**:
   ```bash
   cat > terraform/terraform.tfvars << EOF
   certificate_arn = "arn:aws:acm:us-east-1:123456789012:certificate/your-cert-id"
   environment = "gladly-prod"
   aws_region = "us-east-1"
   EOF
   ```

3. **Deploy**:
   ```bash
   cd terraform
   terraform init
   terraform plan
   terraform apply
   ```

## Step-by-Step Deployment Instructions

### 1. Prepare Your Environment

```bash
# Clone your repository (if not already done)
git clone https://github.com/YOUR_USERNAME/gladly-conversation-analyzer
cd gladly-conversation-analyzer

# Set your environment variables
export ANTHROPIC_API_KEY="your-anthropic-api-key"
export GLADLY_API_KEY="your-gladly-api-key"
export GLADLY_AGENT_EMAIL="your.email@company.com"
export S3_BUCKET_NAME="your-s3-bucket-name"
export AWS_ACCESS_KEY_ID="your-aws-access-key"
export AWS_SECRET_ACCESS_KEY="your-aws-secret-key"
```

### 2. Deploy Infrastructure

```bash
# Navigate to terraform directory
cd terraform

# Initialize Terraform
terraform init

# Plan the deployment
terraform plan

# Apply the changes
terraform apply
```

### 3. Update Your Application

After the infrastructure is deployed, update your application:

```bash
# Go back to project root
cd ..

# Deploy your application
./deploy.sh production
```

### 4. Verify HTTPS Setup

1. **Check Load Balancer Status**:
   ```bash
   aws elbv2 describe-load-balancers --region us-east-1
   ```

2. **Test HTTPS Connection**:
   ```bash
   curl -I https://your-load-balancer-dns-name.elb.amazonaws.com
   ```

3. **Check Certificate Status**:
   ```bash
   aws acm list-certificates --region us-east-1
   ```

## Troubleshooting

### Common Issues

1. **Certificate Validation Failed**:
   - Ensure DNS records are properly configured
   - Wait 10-15 minutes for DNS propagation
   - Check Route53 zone configuration

2. **Load Balancer Health Checks Failing**:
   - Verify your application is running on port 5000
   - Check security group allows traffic on port 5000
   - Ensure health check endpoint `/health` is responding

3. **HTTPS Not Working**:
   - Verify SSL certificate is attached to the HTTPS listener
   - Check security group allows traffic on port 443
   - Ensure load balancer is in the correct subnets

### Useful Commands

```bash
# Check load balancer listeners
aws elbv2 describe-listeners --load-balancer-arn your-lb-arn --region us-east-1

# Check target group health
aws elbv2 describe-target-health --target-group-arn your-tg-arn --region us-east-1

# Check certificate details
aws acm describe-certificate --certificate-arn your-cert-arn --region us-east-1
```

## Security Considerations

1. **Security Groups**: The updated configuration includes proper security group rules for HTTPS (port 443).

2. **SSL Policy**: Uses `ELBSecurityPolicy-TLS-1-2-2017-01` which provides strong security.

3. **HTTP Redirect**: All HTTP traffic is automatically redirected to HTTPS.

4. **Certificate Management**: Certificates are automatically renewed by AWS Certificate Manager.

## Cost Considerations

- **Application Load Balancer**: ~$16/month + data processing costs
- **SSL Certificate**: Free with AWS Certificate Manager
- **Route53**: ~$0.50/month per hosted zone (if using custom domain)

## Next Steps

After successful deployment:

1. Update your application's frontend to use HTTPS URLs
2. Update any hardcoded HTTP URLs in your code
3. Test all functionality over HTTPS
4. Consider setting up monitoring and alerting for your HTTPS endpoints

## Support

If you encounter issues:

1. Check the AWS CloudWatch logs for your load balancer
2. Verify all environment variables are set correctly
3. Ensure your application is healthy and responding to health checks
4. Check the Terraform state for any failed resources

Your application should now be accessible via HTTPS at your load balancer's DNS name or custom domain!

