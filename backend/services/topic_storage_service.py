"""
Topic Storage Service

Stores extracted conversation topics by date for efficient retrieval.
Uses S3 for persistence (with local fallback).
"""

import json
import os
import boto3
from datetime import datetime
from typing import Dict, Optional, List
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
        self.topics_by_date: Dict[str, Dict[str, str]] = self._load_topics()
    
    def _load_topics(self) -> Dict[str, Dict[str, str]]:
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
    
    def _load_from_s3(self) -> Dict[str, Dict[str, str]]:
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
    
    def save_topics_for_date(self, date: str, topic_mapping: Dict[str, str]):
        """Save topic mappings for a specific date"""
        self.topics_by_date[date] = topic_mapping
        self._save_topics()
        logger.info(f"Saved topics for date {date}: {len(topic_mapping)} conversations")
    
    def get_topics_for_date(self, date: str) -> Optional[Dict[str, str]]:
        """Get topic mappings for a specific date"""
        return self.topics_by_date.get(date)
    
    def get_extraction_status(self) -> Dict[str, Dict[str, int]]:
        """Get status of extracted topics by date"""
        status = {}
        for date, topic_mapping in self.topics_by_date.items():
            status[date] = {
                'conversation_count': len(topic_mapping),
                'unique_topics': len(set(topic_mapping.values()))
            }
        return status
    
    def has_topics_for_date(self, date: str) -> bool:
        """Check if topics exist for a date"""
        return date in self.topics_by_date and len(self.topics_by_date[date]) > 0

