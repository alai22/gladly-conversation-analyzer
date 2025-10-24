@echo off
REM HTTPS Deployment Script for Gladly Conversation Analyzer (Windows)
REM This script helps deploy your application with HTTPS support

setlocal enabledelayedexpansion

echo 🚀 HTTPS Deployment Script for Gladly Conversation Analyzer
echo ============================================================

REM Default values
set DOMAIN_NAME=
set CERTIFICATE_ARN=
set ENVIRONMENT=gladly-prod
set AWS_REGION=us-east-1

REM Parse command line arguments
:parse_args
if "%~1"=="" goto check_prereqs
if "%~1"=="--domain" (
    set DOMAIN_NAME=%~2
    shift
    shift
    goto parse_args
)
if "%~1"=="--certificate-arn" (
    set CERTIFICATE_ARN=%~2
    shift
    shift
    goto parse_args
)
if "%~1"=="--environment" (
    set ENVIRONMENT=%~2
    shift
    shift
    goto parse_args
)
if "%~1"=="--region" (
    set AWS_REGION=%~2
    shift
    shift
    goto parse_args
)
if "%~1"=="--help" (
    echo Usage: %0 [OPTIONS]
    echo.
    echo Options:
    echo   --domain DOMAIN          Custom domain name (optional)
    echo   --certificate-arn ARN    Existing SSL certificate ARN (optional)
    echo   --environment ENV        Environment name (default: gladly-prod)
    echo   --region REGION          AWS region (default: us-east-1)
    echo   --help                   Show this help message
    echo.
    echo Examples:
    echo   %0                                    # Deploy with AWS default certificate
    echo   %0 --domain myapp.com                # Deploy with custom domain
    echo   %0 --certificate-arn arn:aws:acm:... # Deploy with existing certificate
    exit /b 0
)
echo Unknown option: %~1
echo Use --help for usage information
exit /b 1

:check_prereqs
echo ℹ Checking prerequisites...

REM Check if AWS CLI is installed
aws --version >nul 2>&1
if errorlevel 1 (
    echo ✗ AWS CLI is not installed. Please install it first.
    exit /b 1
)
echo ✓ AWS CLI is installed

REM Check if Terraform is installed
terraform --version >nul 2>&1
if errorlevel 1 (
    echo ✗ Terraform is not installed. Please install it first.
    exit /b 1
)
echo ✓ Terraform is installed

REM Check if Docker is running
docker info >nul 2>&1
if errorlevel 1 (
    echo ✗ Docker is not running. Please start Docker and try again.
    exit /b 1
)
echo ✓ Docker is running

REM Check AWS credentials
aws sts get-caller-identity >nul 2>&1
if errorlevel 1 (
    echo ✗ AWS credentials not configured. Please run 'aws configure' first.
    exit /b 1
)
echo ✓ AWS credentials configured

REM Check required environment variables
echo ℹ Checking environment variables...

if "%ANTHROPIC_API_KEY%"=="" (
    echo ✗ Required environment variable ANTHROPIC_API_KEY is not set
    exit /b 1
)
echo ✓ ANTHROPIC_API_KEY is set

if "%GLADLY_API_KEY%"=="" (
    echo ✗ Required environment variable GLADLY_API_KEY is not set
    exit /b 1
)
echo ✓ GLADLY_API_KEY is set

if "%GLADLY_AGENT_EMAIL%"=="" (
    echo ✗ Required environment variable GLADLY_AGENT_EMAIL is not set
    exit /b 1
)
echo ✓ GLADLY_AGENT_EMAIL is set

if "%S3_BUCKET_NAME%"=="" (
    echo ✗ Required environment variable S3_BUCKET_NAME is not set
    exit /b 1
)
echo ✓ S3_BUCKET_NAME is set

if "%AWS_ACCESS_KEY_ID%"=="" (
    echo ✗ Required environment variable AWS_ACCESS_KEY_ID is not set
    exit /b 1
)
echo ✓ AWS_ACCESS_KEY_ID is set

if "%AWS_SECRET_ACCESS_KEY%"=="" (
    echo ✗ Required environment variable AWS_SECRET_ACCESS_KEY is not set
    exit /b 1
)
echo ✓ AWS_SECRET_ACCESS_KEY is set

REM Create terraform.tfvars file
echo ℹ Creating Terraform configuration...

echo environment = "%ENVIRONMENT%" > terraform\terraform.tfvars
echo aws_region = "%AWS_REGION%" >> terraform\terraform.tfvars

if not "%DOMAIN_NAME%"=="" (
    echo domain_name = "%DOMAIN_NAME%" >> terraform\terraform.tfvars
    echo ✓ Custom domain configured: %DOMAIN_NAME%
)

if not "%CERTIFICATE_ARN%"=="" (
    echo certificate_arn = "%CERTIFICATE_ARN%" >> terraform\terraform.tfvars
    echo ✓ Existing certificate configured: %CERTIFICATE_ARN%
)

REM Deploy infrastructure
echo ℹ Deploying infrastructure with Terraform...

cd terraform

REM Initialize Terraform
echo ✓ Initializing Terraform...
terraform init

REM Plan deployment
echo ✓ Planning deployment...
terraform plan

REM Ask for confirmation
echo.
echo ⚠ This will deploy/update your AWS infrastructure. Continue? (y/N)
set /p response=
if /i not "%response%"=="y" (
    echo ℹ Deployment cancelled by user
    exit /b 0
)

REM Apply changes
echo ✓ Applying Terraform changes...
terraform apply -auto-approve

REM Get outputs
echo ✓ Getting deployment outputs...
for /f "tokens=*" %%i in ('terraform output -raw application_url') do set APP_URL=%%i
for /f "tokens=*" %%i in ('terraform output -raw application_url_http') do set APP_URL_HTTP=%%i

echo ✓ Infrastructure deployed successfully!

REM Go back to project root
cd ..

REM Deploy application
echo ℹ Deploying application...

REM Build and deploy the application
echo ✓ Building Docker image...
docker build -t gladly-conversation-analyzer:%ENVIRONMENT% .

echo ✓ Deploying application container...
docker run -d ^
    -p 80:5000 ^
    --restart unless-stopped ^
    -e ANTHROPIC_API_KEY="%ANTHROPIC_API_KEY%" ^
    -e GLADLY_API_KEY="%GLADLY_API_KEY%" ^
    -e GLADLY_AGENT_EMAIL="%GLADLY_AGENT_EMAIL%" ^
    -e S3_BUCKET_NAME="%S3_BUCKET_NAME%" ^
    -e AWS_DEFAULT_REGION="%AWS_REGION%" ^
    -e AWS_REGION="%AWS_REGION%" ^
    -e AWS_ACCESS_KEY_ID="%AWS_ACCESS_KEY_ID%" ^
    -e AWS_SECRET_ACCESS_KEY="%AWS_SECRET_ACCESS_KEY%" ^
    --name gladly-prod ^
    gladly-conversation-analyzer:%ENVIRONMENT%

REM Wait for application to start
echo ✓ Waiting for application to start...
timeout /t 30 /nobreak >nul

REM Display results
echo.
echo 🎉 Deployment Complete!
echo =======================
echo.
echo ✓ Your application is now available at:
echo   HTTPS: %APP_URL%
echo   HTTP:  %APP_URL_HTTP% (redirects to HTTPS)
echo.

if not "%DOMAIN_NAME%"=="" (
    echo Custom domain: https://%DOMAIN_NAME%
    echo.
    echo ⚠ Don't forget to configure your DNS:
    echo   Create a CNAME record pointing %DOMAIN_NAME% to your load balancer DNS
    echo.
)

echo ℹ Useful commands:
echo   Check application logs: docker logs gladly-prod
echo   Check load balancer: aws elbv2 describe-load-balancers --region %AWS_REGION%
echo   Test HTTPS: curl -I %APP_URL%
echo.

echo ✓ HTTPS deployment completed successfully!

