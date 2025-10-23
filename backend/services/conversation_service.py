"""
Conversation data service
"""

from typing import List, Dict, Optional, Any
from ..utils.config import Config
from ..utils.logging import get_logger
from ..models.conversation import ConversationItem, ConversationSummary
from .storage_service import StorageService

logger = get_logger('conversation_service')


class ConversationService:
    """Service for managing conversation data"""
    
    def __init__(self, storage_service: Optional[StorageService] = None):
        """Initialize conversation service"""
        self.storage_service = storage_service or StorageService()
        self.conversations: List[ConversationItem] = []
        self.load_conversations()
    
    def load_conversations(self):
        """Load conversations from storage"""
        try:
            raw_conversations = self.storage_service.load_conversations()
            self.conversations = [
                ConversationItem.from_dict(conv) for conv in raw_conversations
            ]
            logger.info(f"Conversations loaded: {len(self.conversations)}")
        except Exception as e:
            logger.error(f"Failed to load conversations: {str(e)}")
            self.conversations = []
    
    def get_summary(self) -> ConversationSummary:
        """Get conversation data summary"""
        if not self.conversations:
            return ConversationSummary(
                total_items=0,
                unique_customers=0,
                unique_conversations=0,
                date_range={'start': 'Unknown', 'end': 'Unknown'},
                content_types={}
            )
        
        # Count by content type
        content_types = {}
        message_types = {}
        customer_ids = set()
        conversation_ids = set()
        timestamps = []
        
        for item in self.conversations:
            # Content types
            content_type = item.content_type
            content_types[content_type] = content_types.get(content_type, 0) + 1
            
            # Message types for chat messages
            if content_type == 'CHAT_MESSAGE':
                msg_type = item.content.get('messageType', 'UNKNOWN')
                message_types[msg_type] = message_types.get(msg_type, 0) + 1
            
            # Customer and conversation IDs
            if item.customer_id:
                customer_ids.add(item.customer_id)
            if item.conversation_id:
                conversation_ids.add(item.conversation_id)
            
            # Timestamps
            if item.timestamp:
                timestamps.append(item.timestamp)
        
        # Sort dates
        timestamps.sort()
        date_range = {
            'start': timestamps[0] if timestamps else 'Unknown',
            'end': timestamps[-1] if timestamps else 'Unknown'
        }
        
        return ConversationSummary(
            total_items=len(self.conversations),
            unique_customers=len(customer_ids),
            unique_conversations=len(conversation_ids),
            date_range=date_range,
            content_types=content_types,
            message_types=message_types if message_types else None
        )
    
    def search_conversations(self, query: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Search conversations for specific content"""
        if not self.conversations:
            return []
        
        query_lower = query.lower()
        results = []
        
        for item in self.conversations:
            if query_lower in item.searchable_text:
                results.append(item.to_dict())
                if len(results) >= limit:
                    break
        
        logger.info(f"Search completed: query={query}, results_count={len(results)}")
        return results
    
    def semantic_search_conversations(self, query: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Enhanced semantic search with concept mappings"""
        if not self.conversations:
            return []
        
        query_lower = query.lower()
        scored_results = []
        
        # Define concept mappings for better semantic search
        concept_mappings = {
            'complaint': ['complaint', 'issue', 'problem', 'concern', 'disappointed', 'frustrated', 'unhappy', 'unsatisfied'],
            'refund': ['refund', 'return', 'money back', 'reimbursement', 'credit', 'compensation'],
            'quality': ['quality', 'defective', 'broken', 'malfunction', 'faulty', 'poor quality', 'bad quality'],
            'safety': ['safety', 'unsafe', 'dangerous', 'hazard', 'risk', 'harmful'],
            'shipping': ['shipping', 'delivery', 'shipped', 'tracking', 'package', 'mail'],
            'battery': ['battery', 'charge', 'charging', 'power', 'dead battery', 'low battery'],
            'gps': ['gps', 'location', 'tracking', 'coordinates', 'position', 'map'],
            'app': ['app', 'application', 'software', 'mobile', 'phone', 'device'],
            'customer_service': ['customer service', 'support', 'help', 'assistance', 'agent', 'representative']
        }
        
        # Find related concepts
        related_terms = set()
        for concept, terms in concept_mappings.items():
            if any(term in query_lower for term in terms):
                related_terms.update(terms)
        
        # Add original query terms
        related_terms.update(query.split())
        
        for item in self.conversations:
            score = 0
            
            # Calculate relevance score
            for term in related_terms:
                term_lower = term.lower()
                if term_lower in item.searchable_text:
                    # Higher score for exact matches
                    if term_lower == query_lower:
                        score += 10
                    # Medium score for related terms
                    elif term_lower in concept_mappings.get(query_lower, []):
                        score += 5
                    # Lower score for other related terms
                    else:
                        score += 1
            
            if score > 0:
                scored_results.append((item.to_dict(), score))
        
        # Sort by relevance score and return top results
        scored_results.sort(key=lambda x: x[1], reverse=True)
        results = [item for item, score in scored_results[:limit]]
        
        logger.info(f"Semantic search completed: query={query}, results_count={len(results)}")
        return results
    
    def get_recent_conversations(self, hours: int = 24) -> List[Dict[str, Any]]:
        """Get conversations from the last N hours"""
        if not self.conversations:
            return []
        
        from datetime import datetime, timedelta
        cutoff_time = datetime.now() - timedelta(hours=hours)
        recent_conversations = []
        
        for item in self.conversations:
            if item.timestamp:
                try:
                    # Parse timestamp (assuming ISO format)
                    conv_time = datetime.fromisoformat(item.timestamp.replace('Z', '+00:00'))
                    if conv_time >= cutoff_time:
                        recent_conversations.append(item.to_dict())
                except:
                    # If timestamp parsing fails, skip this conversation
                    continue
        
        logger.info(f"Recent conversations retrieved: hours={hours}, count={len(recent_conversations)}")
        return recent_conversations
    
    def refresh_conversations(self):
        """Refresh conversations from storage (useful after aggregation)"""
        logger.info("Refreshing conversations from storage")
        self.load_conversations()
        logger.info(f"Conversations refreshed: {len(self.conversations)}")
    
    def is_available(self) -> bool:
        """Check if conversation service is available"""
        return len(self.conversations) > 0
