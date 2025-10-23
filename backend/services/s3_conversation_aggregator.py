"""
S3 Conversation Aggregation Service

This service aggregates conversation files from S3 into a single file
that the RAG system can use for analysis.
"""

import json
import boto3
import os
from datetime import datetime
from typing import List, Dict, Any, Optional
import logging
from dotenv import load_dotenv

from backend.utils.config import Config

# Load environment variables
load_dotenv()

logger = logging.getLogger(__name__)

class S3ConversationAggregator:
    """Aggregates conversation files from S3 into a single file for RAG system"""
    
    def __init__(self):
        self.s3_client = boto3.client('s3')
        self.bucket_name = Config.S3_BUCKET_NAME
        self.region = Config.S3_REGION
        
        if not self.bucket_name:
            raise ValueError("S3_BUCKET_NAME not configured")
    
    def aggregate_conversations(self, target_key: str = None) -> Dict[str, Any]:
        """
        Aggregate all conversation files from S3 into a single file
        
        Args:
            target_key: S3 key for the aggregated file (defaults to Config.S3_FILE_KEY)
        
        Returns:
            Dict with aggregation statistics
        """
        if target_key is None:
            target_key = Config.S3_FILE_KEY
        
        logger.info(f"Starting conversation aggregation to s3://{self.bucket_name}/{target_key}")
        
        # Get all conversation files from S3
        conversation_files = self._list_conversation_files()
        
        if not conversation_files:
            logger.warning("No conversation files found in S3")
            return {
                'status': 'warning',
                'message': 'No conversation files found',
                'files_processed': 0,
                'total_conversations': 0
            }
        
        # Aggregate conversations
        all_conversations = []
        files_processed = 0
        
        for file_key in conversation_files:
            try:
                conversations = self._load_conversation_file(file_key)
                all_conversations.extend(conversations)
                files_processed += 1
                logger.info(f"Loaded {len(conversations)} conversations from {file_key}")
            except Exception as e:
                logger.error(f"Failed to load {file_key}: {e}")
        
        # Remove duplicates based on conversation ID and timestamp
        unique_conversations = self._deduplicate_conversations(all_conversations)
        
        # Upload aggregated file to S3
        self._upload_aggregated_file(unique_conversations, target_key)
        
        stats = {
            'status': 'success',
            'files_processed': files_processed,
            'total_conversations': len(unique_conversations),
            'duplicates_removed': len(all_conversations) - len(unique_conversations),
            'target_key': target_key,
            'aggregated_at': datetime.now().isoformat()
        }
        
        logger.info(f"Aggregation completed: {stats}")
        return stats
    
    def _list_conversation_files(self) -> List[str]:
        """List all conversation files in S3"""
        try:
            response = self.s3_client.list_objects_v2(
                Bucket=self.bucket_name,
                Prefix='gladly-conversations/'
            )
            
            files = []
            if 'Contents' in response:
                for obj in response['Contents']:
                    key = obj['Key']
                    if key.endswith('.jsonl') and 'gladly_conversations' in key:
                        files.append(key)
            
            # Sort by modification time (newest first)
            files.sort(key=lambda x: response['Contents'][files.index(x)]['LastModified'], reverse=True)
            
            logger.info(f"Found {len(files)} conversation files in S3")
            return files
            
        except Exception as e:
            logger.error(f"Failed to list S3 files: {e}")
            return []
    
    def _load_conversation_file(self, file_key: str) -> List[Dict[str, Any]]:
        """Load conversations from a specific S3 file"""
        try:
            response = self.s3_client.get_object(
                Bucket=self.bucket_name,
                Key=file_key
            )
            
            content = response['Body'].read().decode('utf-8')
            conversations = []
            
            for line in content.split('\n'):
                if line.strip():
                    try:
                        conversations.append(json.loads(line.strip()))
                    except json.JSONDecodeError:
                        logger.warning(f"Failed to parse line in {file_key}: {line[:100]}...")
            
            return conversations
            
        except Exception as e:
            logger.error(f"Failed to load {file_key}: {e}")
            return []
    
    def _deduplicate_conversations(self, conversations: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Remove duplicate conversations based on ID and timestamp"""
        seen = set()
        unique_conversations = []
        
        for conv in conversations:
            # Create a unique key based on conversation ID and timestamp
            conv_id = conv.get('_metadata', {}).get('conversation_id', '')
            timestamp = conv.get('_metadata', {}).get('downloaded_at', '')
            unique_key = f"{conv_id}_{timestamp}"
            
            if unique_key not in seen:
                seen.add(unique_key)
                unique_conversations.append(conv)
        
        logger.info(f"Deduplication: {len(conversations)} -> {len(unique_conversations)} conversations")
        return unique_conversations
    
    def _upload_aggregated_file(self, conversations: List[Dict[str, Any]], target_key: str):
        """Upload aggregated conversations to S3"""
        try:
            # Convert to JSONL format
            jsonl_content = '\n'.join(json.dumps(conv) for conv in conversations)
            
            # Upload to S3
            self.s3_client.put_object(
                Bucket=self.bucket_name,
                Key=target_key,
                Body=jsonl_content.encode('utf-8'),
                ContentType='application/json'
            )
            
            logger.info(f"Uploaded {len(conversations)} conversations to s3://{self.bucket_name}/{target_key}")
            
        except Exception as e:
            logger.error(f"Failed to upload aggregated file: {e}")
            raise
    
    def get_aggregation_status(self) -> Dict[str, Any]:
        """Get status of current aggregated file"""
        try:
            response = self.s3_client.head_object(
                Bucket=self.bucket_name,
                Key=Config.S3_FILE_KEY
            )
            
            return {
                'exists': True,
                'last_modified': response['LastModified'].isoformat(),
                'size_bytes': response['ContentLength'],
                'size_mb': round(response['ContentLength'] / (1024 * 1024), 2)
            }
            
        except self.s3_client.exceptions.NoSuchKey:
            return {'exists': False}
        except Exception as e:
            logger.error(f"Failed to get aggregation status: {e}")
            return {'exists': False, 'error': str(e)}
    
    def refresh_rag_data(self) -> Dict[str, Any]:
        """Refresh RAG data by re-aggregating conversations"""
        logger.info("Refreshing RAG data with latest conversations")
        
        # Aggregate conversations
        result = self.aggregate_conversations()
        
        if result['status'] == 'success':
            logger.info(f"RAG data refreshed: {result['total_conversations']} conversations from {result['files_processed']} files")
            
            # Trigger RAG system refresh
            try:
                self._trigger_rag_refresh()
            except Exception as e:
                logger.warning(f"Failed to trigger RAG refresh: {e}")
        else:
            logger.warning(f"RAG data refresh failed: {result.get('message', 'Unknown error')}")
        
        return result
    
    def _trigger_rag_refresh(self):
        """Trigger RAG system to refresh conversation data"""
        try:
            import requests
            response = requests.post('http://localhost:5000/api/conversations/refresh', timeout=30)
            if response.status_code == 200:
                logger.info("RAG system refresh triggered successfully")
            else:
                logger.warning(f"RAG refresh failed with status {response.status_code}")
        except Exception as e:
            logger.error(f"Failed to trigger RAG refresh: {e}")
            raise
