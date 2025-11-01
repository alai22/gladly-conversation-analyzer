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
    # Default to claude-3-haiku-20240307 (verified working model)
    # Claude 4 models (claude-sonnet-4, claude-opus-4) may not be available with all API keys
    CLAUDE_MODEL: str = os.getenv('CLAUDE_MODEL', 'claude-3-haiku-20240307')
    CLAUDE_API_TIMEOUT: int = int(os.getenv('CLAUDE_API_TIMEOUT', '120'))  # Default 120 seconds for complex queries
    
    @classmethod
    def get_api_key_status(cls) -> dict:
        """Get status of API key for debugging"""
        key_present = cls.ANTHROPIC_API_KEY is not None
        key_length = len(cls.ANTHROPIC_API_KEY) if cls.ANTHROPIC_API_KEY else 0
        key_prefix = cls.ANTHROPIC_API_KEY[:12] + "..." if key_present and key_length > 12 else "N/A"
        return {
            'present': key_present,
            'length': key_length,
            'prefix': key_prefix
        }
    
    # Model aliases and fallbacks
    # Maps deprecated/unavailable models to working alternatives
    # Note: We don't alias Claude 4 models here - let them be tried first, fallback system handles failures
    MODEL_ALIASES = {
        # Legacy Claude 3.5 models (not available) -> map to working Claude 3
        'claude-3-5-sonnet': 'claude-3-haiku-20240307',
        'claude-3-5-sonnet-20241022': 'claude-3-haiku-20240307',
        'claude-3-5-sonnet-20240620': 'claude-3-haiku-20240307',
        'claude-3-5-haiku-20241022': 'claude-3-haiku-20240307',
        # Legacy Claude 3 models (deprecated/unavailable) -> map to working model
        'claude-3-opus-20240229': 'claude-3-haiku-20240307',
        'claude-3-sonnet-20240229': 'claude-3-haiku-20240307',  # Deprecated, use haiku
    }
    
    # List of verified working models (tested with current API key)
    # Ordered by preference for fallback - put verified working models first
    VERIFIED_MODELS = [
        'claude-3-haiku-20240307',  # Primary - verified working model
        'claude-3-sonnet-20240229',  # May work with some API keys
        'claude-sonnet-4',  # Try Claude 4 models last (may not be available)
        'claude-opus-4',   # Try Claude 4 models last (may not be available)
    ]
    
    # Fallback model if configured model doesn't work
    # Using Haiku as fallback (verified working, cost-effective)
    FALLBACK_MODEL = 'claude-3-haiku-20240307'
    
    @classmethod
    def resolve_model(cls, requested_model: Optional[str] = None) -> str:
        """
        Resolve a model name, applying aliases and fallbacks.
        
        Args:
            requested_model: The requested model name (or None to use default)
            
        Returns:
            A working model name
        """
        model = requested_model or cls.CLAUDE_MODEL
        
        # Check if it's an alias
        if model in cls.MODEL_ALIASES:
            logger = __import__('logging').getLogger('config')
            logger.info(f"Model alias '{model}' mapped to '{cls.MODEL_ALIASES[model]}'")
            return cls.MODEL_ALIASES[model]
        
        return model
    
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
    
    # Survicate Survey Configuration
    SURVICATE_CSV_PATH: str = os.getenv('SURVICATE_CSV_PATH', 'data/survicate_cancelled_subscriptions.csv')
    
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
