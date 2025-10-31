"""
Configuration utilities
"""

import os
from typing import Optional
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


class Config:
    """Application configuration"""
    
    # API Configuration
    ANTHROPIC_API_KEY: Optional[str] = os.getenv('ANTHROPIC_API_KEY')
    CLAUDE_MODEL: str = os.getenv('CLAUDE_MODEL', 'claude-3-5-sonnet')
    
    # Gladly API Configuration
    GLADLY_API_KEY: Optional[str] = os.getenv('GLADLY_API_KEY')
    GLADLY_AGENT_EMAIL: Optional[str] = os.getenv('GLADLY_AGENT_EMAIL')
    
    # Storage Configuration
    STORAGE_TYPE: str = os.getenv('STORAGE_TYPE', 's3')
    S3_BUCKET_NAME: Optional[str] = os.getenv('S3_BUCKET_NAME')
    S3_FILE_KEY: str = os.getenv('S3_FILE_KEY', 'conversation_items.json')
    S3_REGION: str = os.getenv('S3_REGION', 'us-east-2')
    
    # Azure Storage Configuration
    AZURE_CONNECTION_STRING: Optional[str] = os.getenv('AZURE_CONNECTION_STRING')
    AZURE_CONTAINER_NAME: str = os.getenv('AZURE_CONTAINER_NAME', 'gladly-conversations')
    AZURE_BLOB_NAME: str = os.getenv('AZURE_BLOB_NAME', 'conversation_items.jsonl')
    
    # Flask Configuration
    FLASK_ENV: str = os.getenv('FLASK_ENV', 'production')
    FLASK_DEBUG: bool = os.getenv('FLASK_DEBUG', '0').lower() in ('true', '1', 'yes')
    PORT: int = int(os.getenv('PORT', 5000))
    HOST: str = os.getenv('HOST', '0.0.0.0')
    
    # Local file fallback
    LOCAL_FILE_PATH: str = os.getenv('LOCAL_FILE_PATH', 'conversation_items.jsonl')
    
    @classmethod
    def validate(cls) -> bool:
        """Validate required configuration"""
        if not cls.ANTHROPIC_API_KEY:
            print("Warning: ANTHROPIC_API_KEY not set")
            return False
        
        if cls.STORAGE_TYPE == 's3' and not cls.S3_BUCKET_NAME:
            print("Warning: S3_BUCKET_NAME not set for S3 storage")
            return False
        
        if cls.STORAGE_TYPE == 'azure' and not cls.AZURE_CONNECTION_STRING:
            print("Warning: AZURE_CONNECTION_STRING not set for Azure storage")
            return False
        
        return True
