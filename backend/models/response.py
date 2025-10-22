"""
Response data models
"""

from dataclasses import dataclass
from typing import Dict, List, Optional, Any


@dataclass
class ClaudeResponse:
    """Claude API response model"""
    content: str
    model: str
    tokens_used: int
    streamed: bool = False
    
    @classmethod
    def from_api_response(cls, response: Dict[str, Any], model: str, streamed: bool = False) -> 'ClaudeResponse':
        """Create ClaudeResponse from API response"""
        content = ""
        tokens_used = 0
        
        if streamed:
            # Handle streamed response
            for chunk in response:
                if chunk.get('content') and chunk['content']:
                    for content_block in chunk['content']:
                        if content_block.get('type') == 'text':
                            content += content_block['text']
        else:
            # Handle regular response
            if response.get('content') and response['content']:
                for content_block in response['content']:
                    if content_block.get('type') == 'text':
                        content += content_block['text']
            
            tokens_used = response.get('usage', {}).get('output_tokens', 0)
        
        return cls(
            content=content,
            model=model,
            tokens_used=tokens_used,
            streamed=streamed
        )


@dataclass
class RAGStep:
    """Single step in RAG process"""
    step: int
    name: str
    description: str
    status: str  # 'running', 'completed', 'failed'
    details: Optional[Dict[str, Any]] = None
    warning: Optional[str] = None


@dataclass
class RAGProcess:
    """RAG (Retrieval-Augmented Generation) process tracking"""
    steps: List[RAGStep]
    plan: Optional[Dict[str, Any]] = None
    retrieval_stats: Optional[Dict[str, Any]] = None
    data_summary: Optional[Dict[str, Any]] = None
    
    def add_step(self, step: int, name: str, description: str, status: str = 'running'):
        """Add a new step to the RAG process"""
        self.steps.append(RAGStep(step, name, description, status))
    
    def update_step(self, step: int, status: str, details: Optional[Dict[str, Any]] = None, warning: Optional[str] = None):
        """Update an existing step"""
        for rag_step in self.steps:
            if rag_step.step == step:
                rag_step.status = status
                if details:
                    rag_step.details = details
                if warning:
                    rag_step.warning = warning
                break


@dataclass
class SearchResult:
    """Search result model"""
    items: List[Dict[str, Any]]
    count: int
    query: str
    search_type: str  # 'semantic', 'exact'
    
    def to_formatted_string(self) -> str:
        """Convert to formatted string for display"""
        if not self.items:
            return f"No results found for query: '{self.query}'"
        
        formatted_results = []
        for i, item in enumerate(self.items, 1):
            content = item.get('content', {})
            formatted_results.append(
                f"**Result {i}**\n" +
                f"Type: {content.get('type', 'Unknown')}\n" +
                f"Timestamp: {item.get('timestamp', 'Unknown')}\n" +
                f"Customer: {item.get('customerId', 'Unknown')}\n" +
                f"Content: {content.get('content', content.get('subject', content.get('body', 'No content')))}\n"
            )
        
        return '\n---\n'.join(formatted_results)
