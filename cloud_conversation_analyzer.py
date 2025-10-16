import json
import boto3
from azure.storage.blob import BlobServiceClient
import os
from typing import List, Dict, Optional
import tempfile

class CloudConversationAnalyzer:
    def __init__(self, storage_type: str = "s3", **kwargs):
        """
        Initialize conversation analyzer with cloud storage support
        
        Args:
            storage_type: "s3", "azure", or "local"
            **kwargs: Storage-specific configuration
        """
        self.storage_type = storage_type
        self.conversations = []
        
        if storage_type == "s3":
            self.s3_client = boto3.client('s3')
            self.bucket_name = kwargs.get('bucket_name')
            self.file_key = kwargs.get('file_key', 'conversation_items.jsonl')
        elif storage_type == "azure":
            self.blob_client = BlobServiceClient.from_connection_string(
                kwargs.get('connection_string')
            )
            self.container_name = kwargs.get('container_name')
            self.blob_name = kwargs.get('blob_name', 'conversation_items.jsonl')
        else:
            # Local file fallback
            self.local_file = kwargs.get('local_file', 'conversation_items.jsonl')
        
        self.load_conversations()
    
    def load_conversations(self):
        """Load conversations from cloud storage or local file"""
        try:
            if self.storage_type == "s3":
                self._load_from_s3()
            elif self.storage_type == "azure":
                self._load_from_azure()
            else:
                self._load_from_local()
            
            print(f"Loaded {len(self.conversations)} conversation items from {self.storage_type}")
        except Exception as e:
            print(f"Error loading conversations from {self.storage_type}: {e}")
            self.conversations = []
    
    def _load_from_s3(self):
        """Load conversations from S3"""
        response = self.s3_client.get_object(
            Bucket=self.bucket_name,
            Key=self.file_key
        )
        
        content = response['Body'].read().decode('utf-8')
        for line in content.split('\n'):
            if line.strip():
                self.conversations.append(json.loads(line.strip()))
    
    def _load_from_azure(self):
        """Load conversations from Azure Blob Storage"""
        blob_client = self.blob_client.get_blob_client(
            container=self.container_name,
            blob=self.blob_name
        )
        
        content = blob_client.download_blob().readall().decode('utf-8')
        for line in content.split('\n'):
            if line.strip():
                self.conversations.append(json.loads(line.strip()))
    
    def _load_from_local(self):
        """Load conversations from local file"""
        with open(self.local_file, 'r', encoding='utf-8') as f:
            for line in f:
                if line.strip():
                    self.conversations.append(json.loads(line.strip()))
    
    def get_conversation_summary(self) -> str:
        """Get a summary of the conversation data"""
        if not self.conversations:
            return "No conversation data available"
        
        total_items = len(self.conversations)
        
        # Count by content type
        content_types = {}
        for item in self.conversations:
            content_type = item.get('content', {}).get('type', 'Unknown')
            content_types[content_type] = content_types.get(content_type, 0) + 1
        
        # Get date range
        timestamps = [item.get('timestamp', '') for item in self.conversations if item.get('timestamp')]
        date_range = "Unknown"
        if timestamps:
            timestamps.sort()
            date_range = f"{timestamps[0]} to {timestamps[-1]}"
        
        summary = f"Conversation Data Summary:\n"
        summary += f"Total items: {total_items}\n"
        summary += f"Date range: {date_range}\n"
        summary += f"Content types:\n"
        
        for msg_type, count in sorted(content_types.items()):
            summary += f"  - {msg_type}: {count}\n"
        
        return summary
    
    def search_conversations(self, query: str, limit: int = 10) -> List[Dict]:
        """Search conversations for specific content"""
        if not self.conversations:
            return []
        
        query_lower = query.lower()
        results = []
        
        for item in self.conversations:
            searchable_text = ""
            
            content = item.get('content', {})
            if isinstance(content, dict):
                if 'content' in content:
                    searchable_text += str(content['content']).lower() + " "
                if 'subject' in content:
                    searchable_text += str(content['subject']).lower() + " "
                if 'body' in content:
                    searchable_text += str(content['body']).lower() + " "
            
            if query_lower in searchable_text:
                results.append(item)
                if len(results) >= limit:
                    break
        
        return results
    
    def semantic_search_conversations(self, query: str, limit: int = 10) -> List[Dict]:
        """Enhanced semantic search with concept mappings"""
        if not self.conversations:
            return []
        
        query_lower = query.lower()
        scored_results = []
        
        # Concept mappings for better semantic search
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

