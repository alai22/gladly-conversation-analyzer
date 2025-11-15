"""
Topic Storage Service

Stores extracted conversation topics by date for efficient retrieval.
Uses S3 for persistence (with local fallback).
"""

import json
import os
import boto3
from datetime import datetime, timezone
from typing import Dict, Optional, List, Any, Union
from ..utils.config import Config
from ..utils.logging import get_logger

logger = get_logger('topic_storage_service')


class TopicStorageService:
    """Service for storing and retrieving extracted conversation topics"""
    
    def __init__(self, storage_file: str = "data/extracted_topics.json"):
        """Initialize topic storage service"""
        self.storage_file = storage_file
        self.s3_client = None
        self.bucket_name = Config.S3_BUCKET_NAME
        self.s3_key = "conversation-tracking/extracted_topics.json"
        
        # Initialize S3 client if bucket is configured
        if self.bucket_name and self.bucket_name != "your-gladly-conversations-bucket":
            try:
                self.s3_client = boto3.client('s3', region_name=Config.S3_REGION)
            except Exception as e:
                logger.warning(f"Could not initialize S3 client: {e}")
        
        # Load existing topics
        # Format: Dict[date, Dict[conversation_id, topic_or_metadata]]
        # topic_or_metadata can be: str (old format) or Dict (new format with metadata)
        self.topics_by_date: Dict[str, Dict[str, Union[str, Dict[str, Any]]]] = self._load_topics()
    
    def _load_topics(self) -> Dict[str, Dict[str, Union[str, Dict[str, Any]]]]:
        """Load topics from S3 or local file"""
        try:
            # Try S3 first
            if self.s3_client and self.bucket_name:
                return self._load_from_s3()
        except Exception as e:
            logger.warning(f"Failed to load topics from S3: {e}")
        
        # Fallback to local file
        if os.path.exists(self.storage_file):
            try:
                with open(self.storage_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    logger.info(f"Loaded topics from local file: {len(data)} dates")
                    return data
            except Exception as e:
                logger.error(f"Error loading local topics: {e}")
        
        logger.info("No existing topics found, starting fresh")
        return {}
    
    def _load_from_s3(self) -> Dict[str, Dict[str, Union[str, Dict[str, Any]]]]:
        """Load topics from S3"""
        try:
            response = self.s3_client.get_object(
                Bucket=self.bucket_name,
                Key=self.s3_key
            )
            content = response['Body'].read().decode('utf-8')
            data = json.loads(content)
            logger.info(f"Loaded topics from S3: {len(data)} dates")
            return data
        except self.s3_client.exceptions.NoSuchKey:
            logger.info("No topics found in S3, starting fresh")
            return {}
        except Exception as e:
            logger.error(f"Error loading topics from S3: {e}")
            raise
    
    def _save_topics(self):
        """Save topics to S3 and local file"""
        try:
            # Save to S3 first
            if self.s3_client and self.bucket_name:
                self._save_to_s3()
            
            # Also save locally as backup
            self._save_to_local()
        except Exception as e:
            logger.error(f"Error saving topics: {e}")
            # Try local save as fallback
            try:
                self._save_to_local()
            except Exception as local_e:
                logger.error(f"Failed to save locally: {local_e}")
    
    def _save_to_s3(self):
        """Save topics to S3"""
        try:
            content = json.dumps(self.topics_by_date, indent=2)
            self.s3_client.put_object(
                Bucket=self.bucket_name,
                Key=self.s3_key,
                Body=content.encode('utf-8'),
                ContentType='application/json'
            )
            logger.info(f"Saved topics to S3: {len(self.topics_by_date)} dates")
        except Exception as e:
            logger.error(f"Error saving topics to S3: {e}")
            raise
    
    def _save_to_local(self):
        """Save topics to local file"""
        os.makedirs(os.path.dirname(self.storage_file), exist_ok=True)
        with open(self.storage_file, 'w', encoding='utf-8') as f:
            json.dump(self.topics_by_date, f, indent=2)
        logger.info(f"Saved topics to local file: {len(self.topics_by_date)} dates")
    
    def save_topics_for_date(self, date: str, topic_mapping: Dict[str, Union[str, Dict[str, Any]]]):
        """
        Save topic mappings for a specific date
        Supports both old format (conversation_id -> topic string) and new format (conversation_id -> metadata dict)
        """
        # Normalize: convert old string format to new dict format for consistency
        normalized_mapping = {}
        for conv_id, value in topic_mapping.items():
            if isinstance(value, str):
                # Old format: just topic string - mark extracted_at as None (unknown)
                normalized_mapping[conv_id] = {
                    'topic': value,
                    'sentiment': 'Neutral',
                    'customer_sentiment': 'Neutral',
                    'key_phrases': [],
                    'collar_firmware_version': None,
                    'collar_model': None,
                    'collar_serial_number': None,
                    'mobile_app_version': None,
                    'extracted_at': None  # Unknown timestamp for old data
                }
            elif isinstance(value, dict):
                # New format: metadata dict - ensure extracted_at exists and migrate old product_version if present
                if 'extracted_at' not in value:
                    # If missing timestamp, mark as unknown
                    value['extracted_at'] = None
                
                # Migrate old product_version field to new fields if present
                if 'product_version' in value and value['product_version']:
                    # Try to intelligently assign to collar_model (most common case)
                    if 'collar_model' not in value or not value.get('collar_model'):
                        value['collar_model'] = value['product_version']
                    # Remove old field
                    del value['product_version']
                
                # Ensure new fields exist
                if 'collar_firmware_version' not in value:
                    value['collar_firmware_version'] = None
                if 'collar_model' not in value:
                    value['collar_model'] = None
                if 'collar_serial_number' not in value:
                    value['collar_serial_number'] = None
                if 'mobile_app_version' not in value:
                    value['mobile_app_version'] = None
                
                normalized_mapping[conv_id] = value
            else:
                logger.warning(f"Unexpected topic format for {conv_id}: {type(value)}")
                continue
        
        self.topics_by_date[date] = normalized_mapping
        self._save_topics()
        logger.info(f"Saved topics for date {date}: {len(normalized_mapping)} conversations")
    
    def add_topic_for_date(self, date: str, conversation_id: str, topic_or_metadata: Union[str, Dict[str, Any]], save_immediately: bool = False):
        """
        Add a single topic mapping for a date (for incremental saving)
        
        Args:
            date: Date string (YYYY-MM-DD)
            conversation_id: Conversation ID
            topic_or_metadata: Either a topic string (old format) or metadata dict (new format)
            save_immediately: Whether to save immediately to disk/S3
        """
        if date not in self.topics_by_date:
            self.topics_by_date[date] = {}
        
        # Normalize to dict format
        if isinstance(topic_or_metadata, str):
            # Old format: mark extracted_at as None (unknown)
            self.topics_by_date[date][conversation_id] = {
                'topic': topic_or_metadata,
                'sentiment': 'Neutral',
                'customer_sentiment': 'Neutral',
                'key_phrases': [],
                'collar_firmware_version': None,
                'collar_model': None,
                'collar_serial_number': None,
                'mobile_app_version': None,
                'extracted_at': None  # Unknown timestamp for old data
            }
        elif isinstance(topic_or_metadata, dict):
            # Ensure extracted_at exists in metadata dict
            if 'extracted_at' not in topic_or_metadata:
                topic_or_metadata['extracted_at'] = None
            
            # Migrate old product_version field to new fields if present
            if 'product_version' in topic_or_metadata and topic_or_metadata['product_version']:
                # Try to intelligently assign to collar_model (most common case)
                if 'collar_model' not in topic_or_metadata or not topic_or_metadata.get('collar_model'):
                    topic_or_metadata['collar_model'] = topic_or_metadata['product_version']
                # Remove old field
                del topic_or_metadata['product_version']
            
            # Ensure new fields exist
            if 'collar_firmware_version' not in topic_or_metadata:
                topic_or_metadata['collar_firmware_version'] = None
            if 'collar_model' not in topic_or_metadata:
                topic_or_metadata['collar_model'] = None
            if 'collar_serial_number' not in topic_or_metadata:
                topic_or_metadata['collar_serial_number'] = None
            if 'mobile_app_version' not in topic_or_metadata:
                topic_or_metadata['mobile_app_version'] = None
            
            self.topics_by_date[date][conversation_id] = topic_or_metadata
        else:
            logger.warning(f"Unexpected topic format for {conversation_id}: {type(topic_or_metadata)}")
            return
        
        if save_immediately:
            self._save_topics()
    
    def save_topics_incremental(self, date: str, save_every: int = 10):
        """Save topics incrementally (call this periodically during batch processing)"""
        if date in self.topics_by_date:
            self._save_topics()
            logger.debug(f"Incrementally saved topics for date {date}: {len(self.topics_by_date[date])} conversations")
    
    def get_topics_for_date(self, date: str) -> Optional[Dict[str, Union[str, Dict[str, Any]]]]:
        """
        Get topic mappings for a specific date (returns full metadata dict format)
        
        Returns:
            Dict mapping conversation_id -> metadata dict (or topic string for old format)
        """
        return self.topics_by_date.get(date)
    
    def get_topics_only_for_date(self, date: str) -> Optional[Dict[str, str]]:
        """
        Get only topic strings for backward compatibility
        
        Returns:
            Dict mapping conversation_id -> topic string
        """
        full_data = self.get_topics_for_date(date)
        if not full_data:
            return None
        result = {}
        for conv_id, value in full_data.items():
            if isinstance(value, dict):
                result[conv_id] = value.get('topic', 'Other')
            else:
                result[conv_id] = value
        return result
    
    def get_extraction_status(self) -> Dict[str, Dict[str, int]]:
        """Get status of extracted topics by date"""
        status = {}
        for date, topic_mapping in self.topics_by_date.items():
            # Count unique topics (handle both formats)
            topics = set()
            for value in topic_mapping.values():
                if isinstance(value, dict):
                    topics.add(value.get('topic', 'Other'))
                else:
                    topics.add(value)
            
            status[date] = {
                'conversation_count': len(topic_mapping),
                'unique_topics': len(topics)
            }
        return status
    
    def has_topics_for_date(self, date: str) -> bool:
        """Check if topics exist for a date"""
        return date in self.topics_by_date and len(self.topics_by_date[date]) > 0

