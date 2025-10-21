import json
import requests
import os
from typing import List, Dict, Optional

class PublicS3ConversationAnalyzer:
    def __init__(self, bucket_name: str, file_key: str = "conversation_items.json", region: str = "us-east-2"):
        """
        Initialize conversation analyzer with public S3 access
        
        Args:
            bucket_name: S3 bucket name
            file_key: File key in S3
            region: AWS region
        """
        self.bucket_name = bucket_name
        self.file_key = file_key
        self.region = region
        self.conversations = []
        self.load_conversations()
    
    def load_conversations(self):
        """Load conversations from public S3"""
        try:
            # Construct public S3 URL
            s3_url = f"https://{self.bucket_name}.s3.{self.region}.amazonaws.com/{self.file_key}"
            print(f"Loading conversations from: {s3_url}")
            
            # Download from public S3
            response = requests.get(s3_url)
            response.raise_for_status()
            
            # Parse JSON content
            content = response.text
            if self.file_key.endswith('.jsonl') or self.file_key.endswith('.json'):
                # Try JSONL format first (each line is a JSON object)
                for line in content.split('\n'):
                    if line.strip():
                        try:
                            self.conversations.append(json.loads(line.strip()))
                        except json.JSONDecodeError:
                            # If JSONL parsing fails, try as single JSON array
                            try:
                                data = json.loads(content)
                                if isinstance(data, list):
                                    self.conversations = data
                                else:
                                    self.conversations = [data]
                                break
                            except json.JSONDecodeError:
                                print(f"Failed to parse JSON content: {e}")
                                self.conversations = []
                                return
            
            print(f"Loaded {len(self.conversations)} conversation items from public S3")
        except Exception as e:
            print(f"Error loading conversations from S3: {e}")
            self.conversations = []
    
    def get_conversation_summary(self) -> str:
        """Get a summary of the conversation data"""
        if not self.conversations:
            return "No conversation data available"
        
        total_conversations = len(self.conversations)
        return f"Loaded {total_conversations} conversation items from S3 bucket {self.bucket_name}"
    
    def search_conversations(self, query: str, limit: int = 10) -> List[Dict]:
        """Search conversations by query"""
        if not self.conversations:
            return []
        
        results = []
        query_lower = query.lower()
        
        for conv in self.conversations:
            # Simple text search in conversation content
            content = str(conv).lower()
            if query_lower in content:
                results.append(conv)
                if len(results) >= limit:
                    break
        
        return results
    
    def semantic_search_conversations(self, query: str, limit: int = 10) -> List[Dict]:
        """
        Enhanced semantic search that looks for related concepts and synonyms
        
        Args:
            query: Search query
            limit: Maximum number of results to return
            
        Returns:
            List of matching conversation items with relevance scores
        """
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
            searchable_text = ""
            
            content = item.get('content', {})
            if isinstance(content, dict):
                if 'content' in content:
                    searchable_text += str(content['content']).lower() + " "
                if 'subject' in content:
                    searchable_text += str(content['subject']).lower() + " "
                if 'body' in content:
                    searchable_text += str(content['body']).lower() + " "
            
            # Score based on term matches
            for term in related_terms:
                if term.lower() in searchable_text:
                    score += 1
            
            if score > 0:
                scored_results.append((item, score))
        
        # Sort by score and return top results
        scored_results.sort(key=lambda x: x[1], reverse=True)
        return [item for item, score in scored_results[:limit]]
    
    def get_recent_conversations(self, hours: int = 24) -> List[Dict]:
        """Get conversations from the last N hours"""
        if not self.conversations:
            return []
        
        from datetime import datetime, timedelta
        cutoff_time = datetime.now() - timedelta(hours=hours)
        
        recent_conversations = []
        for conv in self.conversations:
            timestamp_str = conv.get('timestamp', '')
            if timestamp_str:
                try:
                    # Parse timestamp (assuming ISO format)
                    conv_time = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
                    if conv_time >= cutoff_time:
                        recent_conversations.append(conv)
                except:
                    # If timestamp parsing fails, skip this conversation
                    continue
        
        return recent_conversations
