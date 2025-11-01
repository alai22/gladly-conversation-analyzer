"""
Storage service for handling different storage backends
"""

import json
import requests
import boto3
from azure.storage.blob import BlobServiceClient
from typing import List, Dict, Any
from ..utils.config import Config
from ..utils.logging import get_logger

logger = get_logger('storage_service')


class StorageService:
    """Service for handling different storage backends"""
    
    def __init__(self, storage_type: str = None):
        """Initialize storage service"""
        self.storage_type = storage_type or Config.STORAGE_TYPE
        
        if self.storage_type == "s3":
            self._init_s3()
        elif self.storage_type == "azure":
            self._init_azure()
        else:
            self._init_local()
    
    def _init_s3(self):
        """Initialize S3 storage"""
        # boto3 will automatically pick up credentials from:
        # 1. Environment variables (AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY)
        # 2. AWS credentials file (~/.aws/credentials)
        # 3. IAM role (on EC2)
        
        # Check if credentials are available
        import os
        has_env_creds = os.getenv('AWS_ACCESS_KEY_ID') and os.getenv('AWS_SECRET_ACCESS_KEY')
        has_profile = os.path.exists(os.path.expanduser('~/.aws/credentials'))
        
        if not has_env_creds and not has_profile:
            logger.warning("No AWS credentials found in environment or ~/.aws/credentials. "
                          "S3 access may fail. Set AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY "
                          "environment variables or configure AWS CLI with 'aws configure'")
        
        self.s3_client = boto3.client('s3', region_name=Config.S3_REGION)
        self.bucket_name = Config.S3_BUCKET_NAME
        self.file_key = Config.S3_FILE_KEY
        self.region = Config.S3_REGION
        
        if not self.bucket_name or self.bucket_name == "your-gladly-conversations-bucket":
            raise ValueError(f"S3_BUCKET_NAME not configured (current value: {self.bucket_name}). Please set S3_BUCKET_NAME environment variable.")
    
    def _init_azure(self):
        """Initialize Azure Blob Storage"""
        if not Config.AZURE_CONNECTION_STRING:
            raise ValueError("AZURE_CONNECTION_STRING not configured")
        
        self.blob_client = BlobServiceClient.from_connection_string(
            Config.AZURE_CONNECTION_STRING
        )
        self.container_name = Config.AZURE_CONTAINER_NAME
        self.blob_name = Config.AZURE_BLOB_NAME
    
    def _init_local(self):
        """Initialize local file storage"""
        self.local_file = Config.LOCAL_FILE_PATH
    
    def load_conversations(self) -> List[Dict[str, Any]]:
        """Load conversations from storage"""
        try:
            if self.storage_type == "s3":
                return self._load_from_s3()
            elif self.storage_type == "azure":
                return self._load_from_azure()
            else:
                return self._load_from_local()
        except Exception as e:
            logger.error(f"Failed to load conversations from storage (type={self.storage_type}): {str(e)}")
            return []
    
    def _load_from_s3(self) -> List[Dict[str, Any]]:
        """Load conversations from S3"""
        try:
            # Try public S3 access first
            s3_url = f"https://{self.bucket_name}.s3.{self.region}.amazonaws.com/{self.file_key}"
            logger.info(f"Attempting to load from public S3: {s3_url}")
            
            response = requests.get(s3_url)
            response.raise_for_status()
            
            content = response.text
            return self._parse_content(content)
            
        except Exception as e:
            logger.warning(f"Public S3 access failed, trying authenticated access: {str(e)}")
            
            # Fallback to authenticated S3 access
            response = self.s3_client.get_object(
                Bucket=self.bucket_name,
                Key=self.file_key
            )
            
            content = response['Body'].read().decode('utf-8')
            return self._parse_content(content)
    
    def _load_from_azure(self) -> List[Dict[str, Any]]:
        """Load conversations from Azure Blob Storage"""
        blob_client = self.blob_client.get_blob_client(
            container=self.container_name,
            blob=self.blob_name
        )
        
        content = blob_client.download_blob().readall().decode('utf-8')
        return self._parse_content(content)
    
    def _load_from_local(self) -> List[Dict[str, Any]]:
        """Load conversations from local file"""
        with open(self.local_file, 'r', encoding='utf-8') as f:
            content = f.read()
            return self._parse_content(content)
    
    def _parse_content(self, content: str) -> List[Dict[str, Any]]:
        """Parse content from storage"""
        conversations = []
        
        # Try JSONL format first (each line is a JSON object)
        for line in content.split('\n'):
            if line.strip():
                try:
                    conversations.append(json.loads(line.strip()))
                except json.JSONDecodeError:
                    # If JSONL parsing fails, try as single JSON array
                    try:
                        data = json.loads(content)
                        if isinstance(data, list):
                            conversations = data
                        else:
                            conversations = [data]
                        break
                    except json.JSONDecodeError:
                        logger.error("Failed to parse JSON content")
                        return []
        
        logger.info(f"Content parsed successfully: {len(conversations)} conversations")
        return conversations
