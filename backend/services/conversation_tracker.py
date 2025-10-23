"""
Conversation Tracking Service

This service tracks individual conversations that have been downloaded,
including their metadata, download timestamps, and status.
Stores tracking data in S3 for persistence across deployments.
"""

import json
import os
import boto3
from datetime import datetime
from typing import List, Dict, Optional
import logging
from dotenv import load_dotenv

from backend.utils.config import Config

# Load environment variables
load_dotenv()

logger = logging.getLogger(__name__)

class ConversationTracker:
    """Tracks downloaded conversations with metadata"""
    
    def __init__(self, tracking_file: str = "data/downloaded_conversations.json"):
        self.tracking_file = tracking_file
        self.s3_client = boto3.client('s3')
        self.bucket_name = Config.S3_BUCKET_NAME
        self.s3_tracking_key = "conversation-tracking/downloaded_conversations.json"
        self.conversations = self._load_tracking_data()
    
    def _load_tracking_data(self) -> Dict[str, Dict]:
        """Load existing tracking data from S3 or local fallback"""
        try:
            # Try to load from S3 first
            if self.bucket_name:
                return self._load_from_s3()
        except Exception as e:
            logger.warning(f"Failed to load tracking data from S3: {e}")
        
        # Fallback to local file
        if os.path.exists(self.tracking_file):
            try:
                with open(self.tracking_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    logger.info(f"Loaded tracking data from local file: {len(data)} conversations")
                    return data
            except Exception as e:
                logger.error(f"Error loading local tracking data: {e}")
        
        logger.info("No existing tracking data found, starting fresh")
        return {}
    
    def _load_from_s3(self) -> Dict[str, Dict]:
        """Load tracking data from S3"""
        try:
            response = self.s3_client.get_object(
                Bucket=self.bucket_name,
                Key=self.s3_tracking_key
            )
            
            content = response['Body'].read().decode('utf-8')
            data = json.loads(content)
            logger.info(f"Loaded tracking data from S3: {len(data)} conversations")
            return data
            
        except self.s3_client.exceptions.NoSuchKey:
            logger.info("No tracking data found in S3, starting fresh")
            return {}
        except Exception as e:
            logger.error(f"Error loading tracking data from S3: {e}")
            raise
    
    def _save_tracking_data(self):
        """Save tracking data to S3 and local fallback"""
        try:
            # Save to S3 first
            if self.bucket_name:
                self._save_to_s3()
            
            # Also save locally as backup
            self._save_to_local()
            
        except Exception as e:
            logger.error(f"Error saving tracking data: {e}")
            # Try local save as fallback
            try:
                self._save_to_local()
            except Exception as local_e:
                logger.error(f"Failed to save locally as well: {local_e}")
    
    def _save_to_s3(self):
        """Save tracking data to S3"""
        try:
            content = json.dumps(self.conversations, indent=2, ensure_ascii=False)
            
            self.s3_client.put_object(
                Bucket=self.bucket_name,
                Key=self.s3_tracking_key,
                Body=content.encode('utf-8'),
                ContentType='application/json'
            )
            
            logger.debug(f"Saved tracking data to S3: {len(self.conversations)} conversations")
            
        except Exception as e:
            logger.error(f"Error saving tracking data to S3: {e}")
            raise
    
    def _save_to_local(self):
        """Save tracking data to local file"""
        try:
            # Ensure data directory exists
            os.makedirs(os.path.dirname(self.tracking_file), exist_ok=True)
            
            with open(self.tracking_file, 'w', encoding='utf-8') as f:
                json.dump(self.conversations, f, indent=2, ensure_ascii=False)
            
            logger.debug(f"Saved tracking data locally: {len(self.conversations)} conversations")
            
        except Exception as e:
            logger.error(f"Error saving tracking data locally: {e}")
            raise
    
    def track_conversation(self, conversation_id: str, conversation_date: str, 
                          download_timestamp: str, file_name: str, 
                          topics: str = "", channel: str = "", agent: str = ""):
        """Track a downloaded conversation"""
        self.conversations[conversation_id] = {
            'conversation_id': conversation_id,
            'conversation_date': conversation_date,
            'download_timestamp': download_timestamp,
            'file_name': file_name,
            'topics': topics,
            'channel': channel,
            'agent': agent,
            'status': 'downloaded'
        }
        self._save_tracking_data()
        logger.debug(f"Tracked conversation {conversation_id}")
    
    def get_conversation_history(self, limit: int = 100, offset: int = 0) -> List[Dict]:
        """Get conversation download history with pagination"""
        # Sort by download timestamp (newest first)
        sorted_conversations = sorted(
            self.conversations.values(),
            key=lambda x: x['download_timestamp'],
            reverse=True
        )
        
        return sorted_conversations[offset:offset + limit]
    
    def get_conversation_stats(self) -> Dict:
        """Get statistics about downloaded conversations"""
        total_downloaded = len(self.conversations)
        
        if not total_downloaded:
            return {
                'total_downloaded': 0,
                'date_range': {'earliest': None, 'latest': None},
                'channels': {},
                'agents': {},
                'topics': {}
            }
        
        # Get date range
        conversation_dates = [conv['conversation_date'] for conv in self.conversations.values()]
        conversation_dates.sort()
        
        # Count channels
        channels = {}
        agents = {}
        topics = {}
        
        for conv in self.conversations.values():
            # Count channels
            channel = conv.get('channel', 'Unknown')
            channels[channel] = channels.get(channel, 0) + 1
            
            # Count agents
            agent = conv.get('agent', 'Unknown')
            agents[agent] = agents.get(agent, 0) + 1
            
            # Count topics
            topic_list = conv.get('topics', '').split(',') if conv.get('topics') else []
            for topic in topic_list:
                topic = topic.strip()
                if topic:
                    topics[topic] = topics.get(topic, 0) + 1
        
        return {
            'total_downloaded': total_downloaded,
            'date_range': {
                'earliest': conversation_dates[0] if conversation_dates else None,
                'latest': conversation_dates[-1] if conversation_dates else None
            },
            'channels': channels,
            'agents': agents,
            'topics': topics
        }
    
    def migrate_local_to_s3(self):
        """Migrate existing local tracking data to S3"""
        if os.path.exists(self.tracking_file):
            try:
                with open(self.tracking_file, 'r', encoding='utf-8') as f:
                    local_data = json.load(f)
                
                if local_data and self.bucket_name:
                    # Save to S3
                    self.conversations = local_data
                    self._save_to_s3()
                    logger.info(f"Migrated {len(local_data)} conversations from local to S3")
                    return True
            except Exception as e:
                logger.error(f"Failed to migrate local data to S3: {e}")
        
        return False
    
    def is_conversation_downloaded(self, conversation_id: str) -> bool:
        """Check if a conversation has already been downloaded"""
        return conversation_id in self.conversations
    
    def get_downloaded_conversation_ids(self) -> List[str]:
        """Get list of all downloaded conversation IDs"""
        return list(self.conversations.keys())
    
    def get_conversations_by_date_range(self, start_date: str = None, end_date: str = None) -> List[Dict]:
        """Get conversations within a date range"""
        filtered_conversations = []
        
        for conv in self.conversations.values():
            conv_date = conv['conversation_date']
            
            # Check date range
            include_conversation = True
            
            if start_date and conv_date < start_date:
                include_conversation = False
            
            if end_date and conv_date > end_date:
                include_conversation = False
            
            if include_conversation:
                filtered_conversations.append(conv)
        
        # Sort by conversation date
        filtered_conversations.sort(key=lambda x: x['conversation_date'], reverse=True)
        return filtered_conversations
