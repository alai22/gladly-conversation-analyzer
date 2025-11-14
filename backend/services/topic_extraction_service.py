"""
Topic extraction service for conversation analysis
"""

import json
import re
from typing import List, Dict, Optional
from ..utils.config import Config
from ..utils.logging import get_logger
from .claude_service import ClaudeService

logger = get_logger('topic_extraction_service')

# Define conversation topic categories
CONVERSATION_TOPICS = [
    "Product Issues / Technical Problems",
    "Billing / Subscription Questions",
    "Shipping / Delivery Issues",
    "Account Management / Login Issues",
    "Feature Questions / How-to",
    "Returns / Refunds",
    "Product Recommendations / Purchasing",
    "General Customer Service",
    "Other"
]


class TopicExtractionService:
    """Service for extracting topics from conversations using Claude API"""
    
    def __init__(self, claude_service: Optional[ClaudeService] = None):
        """Initialize topic extraction service"""
        self.claude_service = claude_service
        if not self.claude_service:
            # Try to get from service container if available
            # For now, we'll require it to be passed in
            raise ValueError("ClaudeService is required for TopicExtractionService")
    
    def extract_conversation_topic(self, conversation_items: List[Dict]) -> str:
        """
        Extract the primary topic from a conversation using Claude API
        
        Args:
            conversation_items: List of conversation items (messages, notes, etc.)
            
        Returns:
            Topic category string
        """
        if not conversation_items:
            return "Other"
        
        # Format conversation transcript
        transcript = self._format_conversation_transcript(conversation_items)
        
        # Create prompt for Claude
        topic_list = '\n'.join([f'  "{topic}"' for topic in CONVERSATION_TOPICS])
        
        prompt = f"""Analyze this customer support conversation and identify the PRIMARY topic/category.

CONVERSATION TRANSCRIPT:
{transcript}

VALID TOPIC CATEGORIES (use exact spelling):
{topic_list}

INSTRUCTIONS:
1. Read through the entire conversation transcript
2. Identify the PRIMARY topic or main reason for this conversation
3. Choose the SINGLE most appropriate category from the list above
4. Return ONLY the category name (exact match from the list)

RESPONSE FORMAT:
Return ONLY the category name, nothing else. For example:
"Product Issues / Technical Problems"

If the conversation doesn't clearly fit any category, use "Other"."""
        
        try:
            response = self.claude_service.send_message(
                message=prompt,
                model=Config.CLAUDE_MODEL,
                max_tokens=100
            )
            
            topic = response.content.strip().strip('"').strip("'")
            
            # Validate topic is in our list
            if topic in CONVERSATION_TOPICS:
                return topic
            
            # Try fuzzy matching
            topic_lower = topic.lower()
            for valid_topic in CONVERSATION_TOPICS:
                if valid_topic.lower() == topic_lower:
                    return valid_topic
            
            logger.warning(f"Claude returned unexpected topic: '{topic}', using 'Other'")
            return "Other"
            
        except Exception as e:
            logger.error(f"Error extracting topic: {str(e)}")
            return "Other"
    
    def batch_extract_topics(self, conversations: Dict[str, List[Dict]]) -> Dict[str, str]:
        """
        Extract topics for multiple conversations
        
        Args:
            conversations: Dict mapping conversation_id -> list of conversation items
            
        Returns:
            Dict mapping conversation_id -> topic
        """
        results = {}
        
        for conversation_id, items in conversations.items():
            try:
                topic = self.extract_conversation_topic(items)
                results[conversation_id] = topic
                logger.debug(f"Extracted topic '{topic}' for conversation {conversation_id}")
            except Exception as e:
                logger.error(f"Error extracting topic for conversation {conversation_id}: {str(e)}")
                results[conversation_id] = "Other"
        
        return results
    
    def _format_conversation_transcript(self, conversation_items: List[Dict]) -> str:
        """
        Format conversation items into a readable transcript
        
        Args:
            conversation_items: List of conversation items
            
        Returns:
            Formatted transcript string
        """
        # Sort items by timestamp
        sorted_items = sorted(
            conversation_items,
            key=lambda x: x.get('timestamp', ''),
            reverse=False
        )
        
        transcript_parts = []
        
        for item in sorted_items:
            content = item.get('content', {})
            content_type = content.get('type', 'Unknown')
            timestamp = item.get('timestamp', 'No timestamp')
            
            transcript_parts.append(f"\n[{timestamp}] {content_type}:")
            
            # Extract text content based on type
            if 'content' in content:
                transcript_parts.append(f"  {str(content['content'])}")
            if 'subject' in content:
                transcript_parts.append(f"  Subject: {content['subject']}")
            if 'body' in content:
                transcript_parts.append(f"  {str(content['body'])}")
            if 'message' in content:
                transcript_parts.append(f"  {str(content['message'])}")
        
        return '\n'.join(transcript_parts)
