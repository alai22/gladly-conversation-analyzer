# Cloud Storage Configuration
# Copy this to config_cloud.py and update with your credentials

# Storage Type: "s3", "azure", or "local"
STORAGE_TYPE = "s3"

# S3 Configuration
S3_BUCKET_NAME = "your-gladly-conversations-bucket"
S3_FILE_KEY = "conversation_items.jsonl"
S3_REGION = "us-east-1"

# Azure Blob Storage Configuration
AZURE_CONNECTION_STRING = "your-azure-connection-string"
AZURE_CONTAINER_NAME = "gladly-conversations"
AZURE_BLOB_NAME = "conversation_items.jsonl"

# Local fallback
LOCAL_FILE_PATH = "conversation_items.jsonl"

# AWS Credentials (if not using IAM roles)
AWS_ACCESS_KEY_ID = "your-access-key"
AWS_SECRET_ACCESS_KEY = "your-secret-key"

# Anthropic API Configuration
ANTHROPIC_API_KEY = "your-api-key-here"
CLAUDE_MODEL = "claude-3-5-sonnet-20241022"

