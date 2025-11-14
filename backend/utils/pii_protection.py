"""
PII (Personally Identifiable Information) Protection Utilities

This module provides utilities for detecting and redacting PII from data
before sending it to external APIs like Claude.

PII Types Handled:
- Email addresses
- Phone numbers
- Credit card numbers
- Social Security Numbers (SSN)
- Physical addresses
- Names (common patterns)
- Customer/User IDs (can be pseudonymized)
- IP addresses
"""

import re
import hashlib
from typing import Dict, Any, List, Optional, Callable
from ..utils.logging import get_logger

logger = get_logger('pii_protection')


class PIIProtector:
    """Class for detecting and redacting PII from text and data structures"""
    
    # Regex patterns for common PII types
    PATTERNS = {
        'email': re.compile(
            r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',
            re.IGNORECASE
        ),
        'phone': re.compile(
            r'(?:\+?1[-.\s]?)?\(?([0-9]{3})\)?[-.\s]?([0-9]{3})[-.\s]?([0-9]{4})',
            re.IGNORECASE
        ),
        'ssn': re.compile(
            r'\b\d{3}-?\d{2}-?\d{4}\b'
        ),
        'credit_card': re.compile(
            r'\b(?:\d{4}[-\s]?){3}\d{4}\b'
        ),
        'ip_address': re.compile(
            r'\b(?:\d{1,3}\.){3}\d{1,3}\b'
        ),
        # Address patterns (simplified - may have false positives)
        'address_street': re.compile(
            r'\b\d+\s+[A-Za-z0-9\s]+(?:Street|St|Avenue|Ave|Road|Rd|Boulevard|Blvd|Lane|Ln|Drive|Dr|Court|Ct|Way|Circle|Cir)\b',
            re.IGNORECASE
        ),
        # Common name patterns (context-dependent, may have false positives)
        'potential_name': re.compile(
            r'\b(?:Mr|Mrs|Ms|Dr|Prof)\.?\s+[A-Z][a-z]+\s+[A-Z][a-z]+\b'
        ),
    }
    
    def __init__(self, 
                 redact_mode: str = 'hash',
                 preserve_ids: bool = False,
                 enable_name_detection: bool = False):
        """
        Initialize PII protector
        
        Args:
            redact_mode: How to handle PII
                - 'hash': Replace with deterministic hash (same input = same hash)
                - 'redact': Replace with [REDACTED] placeholder
                - 'remove': Remove entirely
            preserve_ids: If True, don't pseudonymize customer/conversation IDs
            enable_name_detection: If True, attempt to detect and redact names
                                    (may have false positives, use with caution)
        """
        self.redact_mode = redact_mode
        self.preserve_ids = preserve_ids
        self.enable_name_detection = enable_name_detection
        
        # Build active patterns based on configuration
        self.active_patterns = {}
        for pii_type, pattern in self.PATTERNS.items():
            if pii_type == 'potential_name' and not enable_name_detection:
                continue
            self.active_patterns[pii_type] = pattern
    
    def hash_value(self, value: str, salt: Optional[str] = None) -> str:
        """Create a deterministic hash of a value"""
        if salt:
            value = f"{value}:{salt}"
        return hashlib.sha256(value.encode()).hexdigest()[:16]  # First 16 chars
    
    def redact_text(self, text: str) -> str:
        """
        Redact PII from text string
        
        Args:
            text: Text to redact
            
        Returns:
            Text with PII redacted
        """
        if not text or not isinstance(text, str):
            return text
        
        result = text
        
        # Process each PII type
        for pii_type, pattern in self.active_patterns.items():
            matches = list(pattern.finditer(result))
            
            # Process matches in reverse order to maintain positions
            for match in reversed(matches):
                original = match.group(0)
                
                if self.redact_mode == 'hash':
                    replacement = f"[{pii_type.upper()}:{self.hash_value(original)}]"
                elif self.redact_mode == 'redact':
                    replacement = f"[REDACTED_{pii_type.upper()}]"
                elif self.redact_mode == 'remove':
                    replacement = ""
                else:
                    replacement = f"[REDACTED_{pii_type.upper()}]"
                
                result = result[:match.start()] + replacement + result[match.end():]
        
        return result
    
    def pseudonymize_id(self, id_value: str, id_type: str = 'customer') -> str:
        """
        Pseudonymize an ID by creating a deterministic hash
        
        Args:
            id_value: Original ID value
            id_type: Type of ID (customer, conversation, user, etc.)
            
        Returns:
            Pseudonymized ID
        """
        if not id_value or self.preserve_ids:
            return id_value
        
        # Use a salt based on ID type for different hash outputs per type
        salt = f"pii_salt_{id_type}"
        hashed = self.hash_value(id_value, salt)
        return f"{id_type[:3].upper()}_{hashed}"
    
    def sanitize_conversation_item(self, item: Dict[str, Any]) -> Dict[str, Any]:
        """
        Sanitize a conversation item by redacting PII
        
        Args:
            item: Conversation item dictionary
            
        Returns:
            Sanitized conversation item
        """
        if not isinstance(item, dict):
            return item
        
        sanitized = item.copy()
        
        # Pseudonymize IDs if configured
        if 'customerId' in sanitized:
            sanitized['customerId'] = self.pseudonymize_id(
                sanitized['customerId'], 
                'customer'
            )
        if 'conversationId' in sanitized:
            sanitized['conversationId'] = self.pseudonymize_id(
                sanitized['conversationId'],
                'conversation'
            )
        
        # Sanitize content fields
        if 'content' in sanitized and isinstance(sanitized['content'], dict):
            content = sanitized['content'].copy()
            
            # Redact text fields in content
            for field in ['content', 'subject', 'body', 'message']:
                if field in content and isinstance(content[field], str):
                    content[field] = self.redact_text(content[field])
            
            sanitized['content'] = content
        
        return sanitized
    
    def sanitize_survey_response(self, survey: Dict[str, Any]) -> Dict[str, Any]:
        """
        Sanitize a survey response by redacting PII
        
        Args:
            survey: Survey response dictionary
            
        Returns:
            Sanitized survey response
        """
        if not isinstance(survey, dict):
            return survey
        
        sanitized = survey.copy()
        
        # Redact email
        if 'email' in sanitized and sanitized['email']:
            if self.redact_mode == 'hash':
                sanitized['email'] = f"[EMAIL:{self.hash_value(sanitized['email'])}]"
            else:
                sanitized['email'] = "[REDACTED_EMAIL]"
        
        # Pseudonymize user ID
        if 'user_id' in sanitized:
            sanitized['user_id'] = self.pseudonymize_id(
                sanitized.get('user_id', ''),
                'user'
            )
        
        # Redact names
        if 'first_name' in sanitized:
            sanitized['first_name'] = "[REDACTED_FIRST_NAME]"
        if 'last_name' in sanitized:
            sanitized['last_name'] = "[REDACTED_LAST_NAME]"
        
        # Sanitize answer text fields
        if 'answers' in sanitized and isinstance(sanitized['answers'], dict):
            sanitized_answers = {}
            for key, value in sanitized['answers'].items():
                if isinstance(value, dict):
                    # Handle Answer/Comment structure
                    sanitized_value = {}
                    for sub_key in ['Answer', 'answer', 'Comment', 'comment']:
                        if sub_key in value and isinstance(value[sub_key], str):
                            sanitized_value[sub_key] = self.redact_text(value[sub_key])
                        elif sub_key in value:
                            sanitized_value[sub_key] = value[sub_key]
                    sanitized_answers[key] = sanitized_value
                elif isinstance(value, str):
                    sanitized_answers[key] = self.redact_text(value)
                else:
                    sanitized_answers[key] = value
            sanitized['answers'] = sanitized_answers
        
        return sanitized
    
    def sanitize_list(self, items: List[Dict[str, Any]], 
                     item_type: str = 'conversation') -> List[Dict[str, Any]]:
        """
        Sanitize a list of items
        
        Args:
            items: List of items to sanitize
            item_type: Type of items ('conversation' or 'survey')
            
        Returns:
            List of sanitized items
        """
        sanitizer = {
            'conversation': self.sanitize_conversation_item,
            'survey': self.sanitize_survey_response
        }.get(item_type, self.sanitize_conversation_item)
        
        return [sanitizer(item) for item in items]


def create_pii_protector(config: Optional[Dict[str, Any]] = None) -> PIIProtector:
    """
    Factory function to create a PII protector from configuration
    
    Args:
        config: Configuration dictionary with keys:
            - redact_mode: 'hash', 'redact', or 'remove' (default: 'hash')
            - preserve_ids: bool (default: False)
            - enable_name_detection: bool (default: False)
            
    Returns:
        Configured PIIProtector instance
    """
    if config is None:
        config = {}
    
    return PIIProtector(
        redact_mode=config.get('redact_mode', 'hash'),
        preserve_ids=config.get('preserve_ids', False),
        enable_name_detection=config.get('enable_name_detection', False)
    )

