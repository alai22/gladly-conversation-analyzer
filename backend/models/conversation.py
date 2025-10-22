"""
Conversation data models
"""

from dataclasses import dataclass
from typing import Dict, List, Optional, Any
from datetime import datetime


@dataclass
class ConversationItem:
    """Represents a single conversation item"""
    id: str
    timestamp: str
    customer_id: str
    conversation_id: str
    content: Dict[str, Any]
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ConversationItem':
        """Create ConversationItem from dictionary"""
        return cls(
            id=data.get('id', ''),
            timestamp=data.get('timestamp', ''),
            customer_id=data.get('customerId', ''),
            conversation_id=data.get('conversationId', ''),
            content=data.get('content', {})
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            'id': self.id,
            'timestamp': self.timestamp,
            'customerId': self.customer_id,
            'conversationId': self.conversation_id,
            'content': self.content
        }
    
    @property
    def content_type(self) -> str:
        """Get the content type"""
        return self.content.get('type', 'Unknown')
    
    @property
    def searchable_text(self) -> str:
        """Get all searchable text content"""
        text_parts = []
        
        if 'content' in self.content:
            text_parts.append(str(self.content['content']))
        if 'subject' in self.content:
            text_parts.append(str(self.content['subject']))
        if 'body' in self.content:
            text_parts.append(str(self.content['body']))
            
        return ' '.join(text_parts).lower()


@dataclass
class ConversationSummary:
    """Summary statistics for conversation data"""
    total_items: int
    unique_customers: int
    unique_conversations: int
    date_range: Dict[str, str]
    content_types: Dict[str, int]
    message_types: Optional[Dict[str, int]] = None
    
    def to_string(self) -> str:
        """Convert to formatted string"""
        summary = f"""Conversation Data Summary:
- Total items: {self.total_items}
- Unique customers: {self.unique_customers}
- Unique conversations: {self.unique_conversations}
- Date range: {self.date_range.get('start', 'Unknown')} to {self.date_range.get('end', 'Unknown')}

Content Types:
"""
        for content_type, count in sorted(self.content_types.items()):
            summary += f"  - {content_type}: {count}\n"
        
        if self.message_types:
            summary += "\nMessage Types:\n"
            for msg_type, count in sorted(self.message_types.items()):
                summary += f"  - {msg_type}: {count}\n"
        
        return summary
