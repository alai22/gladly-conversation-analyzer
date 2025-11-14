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
    # Product Issue Subcategories (replacing broad "Product Issues / Technical Problems")
    "GPS and Location Accuracy Issues",
    "Dog doesn't respond to collar",
    "Battery life, charging or power issues",
    "Feedback Timing / Response Delay Issues",
    "Hardware Reliability Issues",
    # Other Categories
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
    
    def extract_conversation_metadata(self, conversation_items: List[Dict], max_retries: int = 3) -> Dict[str, any]:
        """
        Extract topic and metadata from a conversation using Claude API
        
        Args:
            conversation_items: List of conversation items (messages, notes, etc.)
            max_retries: Maximum number of retries for rate limit errors
            
        Returns:
            Dict with keys: topic, sentiment, customer_sentiment, key_phrases, product_version
        """
        if not conversation_items:
            return {
                'topic': 'Other',
                'sentiment': 'Neutral',
                'customer_sentiment': 'Neutral',
                'key_phrases': [],
                'product_version': None
            }
        
        # Format conversation transcript
        transcript = self._format_conversation_transcript(conversation_items)
        
        # Create prompt for Claude
        topic_list = '\n'.join([f'  "{topic}"' for topic in CONVERSATION_TOPICS])
        
        prompt = f"""Analyze this customer support conversation and extract structured information.

CONVERSATION TRANSCRIPT:
{transcript}

VALID TOPIC CATEGORIES (use exact spelling):
{topic_list}

EXTRACTION REQUIREMENTS:
1. PRIMARY TOPIC: Choose the SINGLE most appropriate category from the list above
   - For product issues, use the MOST SPECIFIC category:
     * GPS/location problems → "GPS and Location Accuracy Issues"
     * Collar not responding → "Dog doesn't respond to collar"
     * Battery/charging/power → "Battery life, charging or power issues"
     * Delayed notifications → "Feedback Timing / Response Delay Issues"
     * Hardware breaking → "Hardware Reliability Issues"

2. SENTIMENT: Overall sentiment of the conversation
   - Options: "Positive", "Negative", "Neutral"
   - Consider the overall tone and outcome

3. CUSTOMER SENTIMENT: Specific customer emotional state
   - Options: "Frustrated", "Satisfied", "Neutral", "Angry", "Happy", "Concerned"
   - Focus on the customer's expressed emotions

4. KEY PHRASES: Extract 2-5 important phrases or keywords that capture the main issue
   - Examples: "GPS not accurate", "battery dies quickly", "collar won't respond"
   - Return as a JSON array of strings
   - Maximum 5 phrases, keep them concise (3-8 words each)

5. PRODUCT VERSION: Extract product model or version if mentioned
   - Look for: version numbers (v2.1, version 3, etc.), model names, product IDs
   - Return the exact text mentioned, or null if not found
   - Examples: "v2.1", "Halo 3", "Model X", null

RESPONSE FORMAT (JSON only, no other text):
{{
  "topic": "GPS and Location Accuracy Issues",
  "sentiment": "Negative",
  "customer_sentiment": "Frustrated",
  "key_phrases": ["GPS not accurate", "location wrong", "pin placement off"],
  "product_version": "v2.1"
}}"""
        
        for attempt in range(max_retries):
            try:
                response = self.claude_service.send_message(
                    message=prompt,
                    model=Config.CLAUDE_MODEL,
                    max_tokens=200  # Increased for structured response
                )
                
                # Parse JSON response
                content = response.content.strip()
                # Remove markdown code blocks if present
                if content.startswith('```'):
                    parts = content.split('```')
                    if len(parts) >= 2:
                        content = parts[1]
                        if content.startswith('json'):
                            content = content[4:]
                    content = content.strip()
                
                metadata = json.loads(content)
                
                # Validate and normalize
                result = {
                    'topic': self._validate_topic(metadata.get('topic', 'Other')),
                    'sentiment': self._validate_sentiment(metadata.get('sentiment', 'Neutral')),
                    'customer_sentiment': self._validate_customer_sentiment(metadata.get('customer_sentiment', 'Neutral')),
                    'key_phrases': self._validate_key_phrases(metadata.get('key_phrases', [])),
                    'product_version': metadata.get('product_version') or None
                }
                
                return result
                
            except json.JSONDecodeError as e:
                logger.warning(f"Failed to parse JSON response (attempt {attempt + 1}/{max_retries}): {e}")
                logger.debug(f"Response content: {response.content[:500] if 'response' in locals() else 'N/A'}")
                if attempt < max_retries - 1:
                    # Try again with a simpler prompt as fallback
                    continue
                # Final fallback: extract just topic
                topic = self._extract_topic_fallback(conversation_items)
                return {
                    'topic': topic,
                    'sentiment': 'Neutral',
                    'customer_sentiment': 'Neutral',
                    'key_phrases': [],
                    'product_version': None
                }
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
                    logger.error(f"HTTP error extracting metadata (status={status_code}): {error_msg}")
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
                    logger.error(f"Error extracting metadata: {error_msg}")
                    if attempt < max_retries - 1:
                        wait_time = min(2 ** attempt, 5)
                        time.sleep(wait_time)
                        continue
                    raise Exception(f"Failed to extract metadata after {max_retries} attempts: {error_msg}")
        
        # Final fallback if all retries failed
        return {
            'topic': 'Other',
            'sentiment': 'Neutral',
            'customer_sentiment': 'Neutral',
            'key_phrases': [],
            'product_version': None
        }
    
    def extract_conversation_topic(self, conversation_items: List[Dict], max_retries: int = 3) -> str:
        """
        Extract the primary topic from a conversation (backward compatibility method)
        
        Args:
            conversation_items: List of conversation items (messages, notes, etc.)
            max_retries: Maximum number of retries for rate limit errors
            
        Returns:
            Topic category string
        """
        metadata = self.extract_conversation_metadata(conversation_items, max_retries)
        return metadata['topic']
    
    def _validate_topic(self, topic: str) -> str:
        """Validate topic is in our list"""
        if not topic or not isinstance(topic, str):
            return "Other"
        if topic in CONVERSATION_TOPICS:
            return topic
        topic_lower = topic.lower()
        for valid_topic in CONVERSATION_TOPICS:
            if valid_topic.lower() == topic_lower:
                return valid_topic
        logger.warning(f"Invalid topic '{topic}', using 'Other'")
        return "Other"
    
    def _validate_sentiment(self, sentiment: str) -> str:
        """Validate sentiment"""
        if not sentiment or not isinstance(sentiment, str):
            return 'Neutral'
        valid = ['Positive', 'Negative', 'Neutral']
        if sentiment in valid:
            return sentiment
        sentiment_lower = sentiment.lower()
        if 'positive' in sentiment_lower or 'good' in sentiment_lower:
            return 'Positive'
        elif 'negative' in sentiment_lower or 'bad' in sentiment_lower:
            return 'Negative'
        return 'Neutral'
    
    def _validate_customer_sentiment(self, sentiment: str) -> str:
        """Validate customer sentiment"""
        if not sentiment or not isinstance(sentiment, str):
            return 'Neutral'
        valid = ['Frustrated', 'Satisfied', 'Neutral', 'Angry', 'Happy', 'Concerned']
        if sentiment in valid:
            return sentiment
        sentiment_lower = sentiment.lower()
        if 'frustrat' in sentiment_lower:
            return 'Frustrated'
        elif 'satisf' in sentiment_lower or 'happy' in sentiment_lower:
            return 'Satisfied'
        elif 'angry' in sentiment_lower or 'mad' in sentiment_lower:
            return 'Angry'
        elif 'concern' in sentiment_lower or 'worri' in sentiment_lower:
            return 'Concerned'
        return 'Neutral'
    
    def _validate_key_phrases(self, phrases: any) -> List[str]:
        """Validate and clean key phrases"""
        if not isinstance(phrases, list):
            return []
        # Limit to 5 phrases, clean them
        cleaned = []
        for phrase in phrases[:5]:
            if isinstance(phrase, str) and phrase.strip():
                cleaned.append(phrase.strip()[:100])  # Max 100 chars per phrase
        return cleaned
    
    def _extract_topic_fallback(self, conversation_items: List[Dict]) -> str:
        """Fallback topic extraction if JSON parsing fails"""
        # Use a simple prompt to extract just the topic
        transcript = self._format_conversation_transcript(conversation_items)
        topic_list = '\n'.join([f'  "{topic}"' for topic in CONVERSATION_TOPICS])
        
        prompt = f"""Analyze this customer support conversation and identify the PRIMARY topic/category.

CONVERSATION TRANSCRIPT:
{transcript}

VALID TOPIC CATEGORIES (use exact spelling):
{topic_list}

Return ONLY the category name, nothing else."""
        
        try:
            response = self.claude_service.send_message(
                message=prompt,
                model=Config.CLAUDE_MODEL,
                max_tokens=100
            )
            topic = response.content.strip().strip('"').strip("'")
            return self._validate_topic(topic)
        except Exception as e:
            logger.error(f"Fallback topic extraction failed: {e}")
            return "Other"
    
    def batch_extract_topics(self, conversations: Dict[str, List[Dict]], 
                            delay_between_requests: float = 0.5,
                            progress_callback: Optional[Callable[[int, int, int, int], None]] = None,
                            incremental_save_callback: Optional[Callable[[str, Dict], None]] = None,
                            save_every: int = 10) -> Dict[str, Dict]:
        """
        Extract topics and metadata for multiple conversations with rate limiting and incremental saving
        
        Args:
            conversations: Dict mapping conversation_id -> list of conversation items
            delay_between_requests: Delay in seconds between API requests (default 0.5s)
            progress_callback: Optional callback function(current, total, success, failed)
            incremental_save_callback: Optional callback(conversation_id, metadata_dict) for incremental saving
            save_every: Save incrementally every N conversations (default 10)
            
        Returns:
            Dict mapping conversation_id -> metadata dict (topic, sentiment, customer_sentiment, key_phrases, product_version)
        """
        results = {}
        total = len(conversations)
        success_count = 0
        failed_count = 0
        
        logger.info(f"Starting batch topic and metadata extraction for {total} conversations with {delay_between_requests}s delay between requests")
        logger.info(f"Estimated time: ~{total * delay_between_requests / 60:.1f} minutes (plus API call time)")
        
        for idx, (conversation_id, items) in enumerate(conversations.items(), 1):
            try:
                # Add delay before each request (except the first one)
                if idx > 1:
                    time.sleep(delay_between_requests)
                
                metadata = self.extract_conversation_metadata(items)
                results[conversation_id] = metadata
                success_count += 1
                
                # Log progress every 10 conversations or at milestones
                if idx % 10 == 0 or idx == total:
                    logger.info(f"Progress: {idx}/{total} conversations processed ({success_count} succeeded, {failed_count} failed) - {idx*100//total}%")
                else:
                    logger.debug(f"Extracted metadata for conversation {conversation_id} ({idx}/{total}): topic={metadata.get('topic')}, sentiment={metadata.get('sentiment')}")
                
                # Incremental save callback (for saving progress as we go)
                if incremental_save_callback:
                    incremental_save_callback(conversation_id, metadata)
                    # Save periodically to avoid too many writes
                    if idx % save_every == 0:
                        logger.debug(f"Incremental save checkpoint: {idx} conversations processed")
                
                # Call progress callback if provided
                if progress_callback:
                    progress_callback(idx, total, success_count, failed_count)
                
            except Exception as e:
                failed_count += 1
                error_msg = str(e)
                logger.error(f"Error extracting metadata for conversation {conversation_id} ({idx}/{total}): {error_msg}")
                
                # If it's a rate limit error, we should stop and let the user know
                if '429' in error_msg or 'rate_limit' in error_msg.lower() or 'Too Many Requests' in error_msg:
                    logger.error(f"Rate limit exceeded. Stopping batch extraction. Processed {success_count}/{total} conversations.")
                    # Save what we have so far
                    if incremental_save_callback:
                        logger.info(f"Saving {success_count} extracted topics before stopping...")
                    raise Exception(f"Rate limit exceeded after processing {success_count} of {total} conversations. "
                                  f"Please wait 1-2 minutes and try again. Partial progress has been saved. Error: {error_msg}")
                
                # For other errors, continue but mark with default values
                default_metadata = {
                    'topic': 'Other',
                    'sentiment': 'Neutral',
                    'customer_sentiment': 'Neutral',
                    'key_phrases': [],
                    'product_version': None
                }
                results[conversation_id] = default_metadata
                
                # Incremental save for failed ones too (with default metadata)
                if incremental_save_callback:
                    incremental_save_callback(conversation_id, default_metadata)
                
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
