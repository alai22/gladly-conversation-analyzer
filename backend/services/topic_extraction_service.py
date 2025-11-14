"""
Topic extraction service for conversation analysis
"""

import json
import re
import time
from typing import List, Dict, Optional, Callable
from requests.exceptions import RequestException, HTTPError
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
    
    def extract_conversation_topic(self, conversation_items: List[Dict], max_retries: int = 3) -> str:
        """
        Extract the primary topic from a conversation using Claude API with retry logic
        
        Args:
            conversation_items: List of conversation items (messages, notes, etc.)
            max_retries: Maximum number of retries for rate limit errors
            
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
        
        for attempt in range(max_retries):
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
                
            except (HTTPError, RequestException) as e:
                error_msg = str(e)
                status_code = None
                
                # Check if we can get status code from the exception
                if hasattr(e, 'response') and e.response is not None:
                    status_code = e.response.status_code
                elif hasattr(e, 'status_code'):
                    status_code = e.status_code
                
                # Handle rate limit errors (429)
                if status_code == 429 or '429' in error_msg or 'rate_limit' in error_msg.lower() or 'Too Many Requests' in error_msg:
                    if attempt < max_retries - 1:
                        # Exponential backoff: wait 2^attempt seconds, max 60 seconds
                        wait_time = min(2 ** attempt, 60)
                        logger.warning(f"Rate limit hit (429), retrying in {wait_time}s (attempt {attempt + 1}/{max_retries})")
                        time.sleep(wait_time)
                        continue
                    else:
                        logger.error(f"Rate limit error after {max_retries} attempts: {error_msg}")
                        raise Exception(f"Rate limit exceeded. Claude API is rate limiting requests. Please wait 1-2 minutes and try again. Details: {error_msg}")
                else:
                    # Other HTTP errors
                    logger.error(f"HTTP error extracting topic (status={status_code}): {error_msg}")
                    if attempt < max_retries - 1:
                        wait_time = min(2 ** attempt, 10)
                        time.sleep(wait_time)
                        continue
                    raise Exception(f"HTTP error ({status_code}): {error_msg}")
            except Exception as e:
                error_msg = str(e)
                # Check if it's a rate limit error in the message
                if '429' in error_msg or 'rate_limit' in error_msg.lower() or 'Too Many Requests' in error_msg:
                    if attempt < max_retries - 1:
                        wait_time = min(2 ** attempt, 60)
                        logger.warning(f"Rate limit detected, retrying in {wait_time}s (attempt {attempt + 1}/{max_retries})")
                        time.sleep(wait_time)
                        continue
                    else:
                        logger.error(f"Rate limit error after {max_retries} attempts: {error_msg}")
                        raise Exception(f"Rate limit exceeded. Claude API is rate limiting requests. Please wait a minute and try again. Details: {error_msg}")
                else:
                    logger.error(f"Error extracting topic: {error_msg}")
                    if attempt < max_retries - 1:
                        wait_time = min(2 ** attempt, 5)
                        time.sleep(wait_time)
                        continue
                    raise Exception(f"Failed to extract topic after {max_retries} attempts: {error_msg}")
        
        # If we get here, all retries failed
        return "Other"
    
    def batch_extract_topics(self, conversations: Dict[str, List[Dict]], 
                            delay_between_requests: float = 0.5,
                            progress_callback: Optional[Callable[[int, int, int, int], None]] = None) -> Dict[str, str]:
        """
        Extract topics for multiple conversations with rate limiting
        
        Args:
            conversations: Dict mapping conversation_id -> list of conversation items
            delay_between_requests: Delay in seconds between API requests (default 0.5s)
            progress_callback: Optional callback function(current, total, success, failed)
            
        Returns:
            Dict mapping conversation_id -> topic
        """
        results = {}
        total = len(conversations)
        success_count = 0
        failed_count = 0
        
        logger.info(f"Starting batch topic extraction for {total} conversations with {delay_between_requests}s delay between requests")
        
        for idx, (conversation_id, items) in enumerate(conversations.items(), 1):
            try:
                # Add delay before each request (except the first one)
                if idx > 1:
                    time.sleep(delay_between_requests)
                
                topic = self.extract_conversation_topic(items)
                results[conversation_id] = topic
                success_count += 1
                logger.debug(f"Extracted topic '{topic}' for conversation {conversation_id} ({idx}/{total})")
                
                # Call progress callback if provided
                if progress_callback:
                    progress_callback(idx, total, success_count, failed_count)
                
            except Exception as e:
                failed_count += 1
                error_msg = str(e)
                logger.error(f"Error extracting topic for conversation {conversation_id} ({idx}/{total}): {error_msg}")
                
                # If it's a rate limit error, we should stop and let the user know
                if '429' in error_msg or 'rate_limit' in error_msg.lower() or 'Too Many Requests' in error_msg:
                    logger.error(f"Rate limit exceeded. Stopping batch extraction. Processed {success_count}/{total} conversations.")
                    raise Exception(f"Rate limit exceeded after processing {success_count} of {total} conversations. "
                                  f"Please wait a minute and try again. Error: {error_msg}")
                
                # For other errors, continue but mark as "Other"
                results[conversation_id] = "Other"
                
                # Call progress callback even on failure
                if progress_callback:
                    progress_callback(idx, total, success_count, failed_count)
        
        logger.info(f"Batch extraction completed: {success_count} succeeded, {failed_count} failed out of {total} total")
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
