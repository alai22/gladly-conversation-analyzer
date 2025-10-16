#!/usr/bin/env python3
"""
Claude API Client - Local script to interact with Claude API
"""

import os
import json
import requests
from typing import Optional, Dict, Any, List
import argparse
import sys
from datetime import datetime
import re

# Try to load local config, fallback to default config
try:
    from config_local import ANTHROPIC_API_KEY, CLAUDE_MODEL, CONVERSATION_FILE
except ImportError:
    try:
        from config import ANTHROPIC_API_KEY, CLAUDE_MODEL, CONVERSATION_FILE
    except ImportError:
        # Fallback to environment variables
        ANTHROPIC_API_KEY = None
        CLAUDE_MODEL = "claude-3-5-sonnet-20241022"
        CONVERSATION_FILE = "conversation_items.jsonl"

class ClaudeAPIClient:
    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize Claude API client
        
        Args:
            api_key: Anthropic API key. If not provided, will look for config file or ANTHROPIC_API_KEY env var
        """
        self.api_key = api_key or ANTHROPIC_API_KEY or os.getenv('ANTHROPIC_API_KEY')
        if not self.api_key:
            raise ValueError("API key not provided. Set ANTHROPIC_API_KEY in config_local.py, config.py, or environment variable")
        
        self.base_url = "https://api.anthropic.com/v1"
        self.headers = {
            "x-api-key": self.api_key,
            "Content-Type": "application/json",
            "anthropic-version": "2023-06-01"
        }
    
    def send_message(self, 
                    message: str, 
                    model: str = "claude-3-5-sonnet-20241022",
                    max_tokens: int = 1000,
                    system_prompt: Optional[str] = None) -> Dict[str, Any]:
        """
        Send a message to Claude API
        
        Args:
            message: The user message to send
            model: Claude model to use
            max_tokens: Maximum tokens in response
            system_prompt: Optional system prompt
            
        Returns:
            API response as dictionary
        """
        payload = {
            "model": model,
            "max_tokens": max_tokens,
            "messages": [
                {
                    "role": "user",
                    "content": message
                }
            ]
        }
        
        if system_prompt:
            payload["system"] = system_prompt
        
        try:
            response = requests.post(
                f"{self.base_url}/messages",
                headers=self.headers,
                json=payload,
                timeout=30
            )
            response.raise_for_status()
            return response.json()
        
        except requests.exceptions.RequestException as e:
            print(f"API request failed: {e}")
            if hasattr(e, 'response') and e.response is not None:
                print(f"Response: {e.response.text}")
            raise
    
    def stream_message(self, 
                     message: str, 
                     model: str = "claude-3-5-sonnet-20241022",
                     max_tokens: int = 1000,
                     system_prompt: Optional[str] = None):
        """
        Stream a message from Claude API
        
        Args:
            message: The user message to send
            model: Claude model to use
            max_tokens: Maximum tokens in response
            system_prompt: Optional system prompt
            
        Yields:
            Chunks of the streaming response
        """
        payload = {
            "model": model,
            "max_tokens": max_tokens,
            "stream": True,
            "messages": [
                {
                    "role": "user",
                    "content": message
                }
            ]
        }
        
        if system_prompt:
            payload["system"] = system_prompt
        
        try:
            response = requests.post(
                f"{self.base_url}/messages",
                headers=self.headers,
                json=payload,
                stream=True,
                timeout=30
            )
            response.raise_for_status()
            
            for line in response.iter_lines():
                if line:
                    line = line.decode('utf-8')
                    if line.startswith('data: '):
                        data = line[6:]  # Remove 'data: ' prefix
                        if data.strip() == '[DONE]':
                            break
                        try:
                            chunk = json.loads(data)
                            yield chunk
                        except json.JSONDecodeError:
                            continue
        
        except requests.exceptions.RequestException as e:
            print(f"Streaming request failed: {e}")
            raise


class ConversationAnalyzer:
    def __init__(self, jsonl_file: str = None):
        """
        Initialize conversation analyzer
        
        Args:
            jsonl_file: Path to the conversation_items.jsonl file
        """
        self.jsonl_file = jsonl_file or CONVERSATION_FILE
        self.conversations = []
        self.load_conversations()
    
    def load_conversations(self):
        """Load conversations from JSONL file"""
        try:
            with open(self.jsonl_file, 'r', encoding='utf-8') as f:
                for line in f:
                    if line.strip():
                        self.conversations.append(json.loads(line.strip()))
            print(f"Loaded {len(self.conversations)} conversation items")
        except FileNotFoundError:
            print(f"Error: {self.jsonl_file} not found")
            self.conversations = []
        except Exception as e:
            print(f"Error loading conversations: {e}")
            self.conversations = []
    
    def get_conversation_summary(self) -> str:
        """Get a summary of the conversation data"""
        if not self.conversations:
            return "No conversation data available"
        
        # Count different types of content
        content_types = {}
        message_types = {}
        customer_ids = set()
        conversation_ids = set()
        date_range = []
        
        for item in self.conversations:
            # Content types
            content_type = item.get('content', {}).get('type', 'UNKNOWN')
            content_types[content_type] = content_types.get(content_type, 0) + 1
            
            # Message types for chat messages
            if content_type == 'CHAT_MESSAGE':
                msg_type = item.get('content', {}).get('messageType', 'UNKNOWN')
                message_types[msg_type] = message_types.get(msg_type, 0) + 1
            
            # Customer and conversation IDs
            if 'customerId' in item:
                customer_ids.add(item['customerId'])
            if 'conversationId' in item:
                conversation_ids.add(item['conversationId'])
            
            # Date range
            if 'timestamp' in item:
                date_range.append(item['timestamp'])
        
        # Sort dates
        date_range.sort()
        start_date = date_range[0] if date_range else "Unknown"
        end_date = date_range[-1] if date_range else "Unknown"
        
        summary = f"""Conversation Data Summary:
- Total items: {len(self.conversations)}
- Unique customers: {len(customer_ids)}
- Unique conversations: {len(conversation_ids)}
- Date range: {start_date} to {end_date}

Content Types:
"""
        for content_type, count in sorted(content_types.items()):
            summary += f"  - {content_type}: {count}\n"
        
        if message_types:
            summary += "\nMessage Types:\n"
            for msg_type, count in sorted(message_types.items()):
                summary += f"  - {msg_type}: {count}\n"
        
        return summary
    
    def search_conversations(self, query: str, limit: int = 10) -> List[Dict]:
        """
        Search conversations for specific content
        
        Args:
            query: Search query
            limit: Maximum number of results to return
            
        Returns:
            List of matching conversation items
        """
        if not self.conversations:
            return []
        
        query_lower = query.lower()
        results = []
        
        for item in self.conversations:
            # Search in various text fields
            searchable_text = ""
            
            # Content field
            content = item.get('content', {})
            if isinstance(content, dict):
                if 'content' in content:
                    searchable_text += str(content['content']).lower() + " "
                if 'subject' in content:
                    searchable_text += str(content['subject']).lower() + " "
                if 'body' in content:
                    searchable_text += str(content['body']).lower() + " "
            
            # Other fields
            if 'customerId' in item:
                searchable_text += str(item['customerId']).lower() + " "
            if 'conversationId' in item:
                searchable_text += str(item['conversationId']).lower() + " "
            
            if query_lower in searchable_text:
                results.append(item)
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
            
            # Content field
            content = item.get('content', {})
            if isinstance(content, dict):
                if 'content' in content:
                    searchable_text += str(content['content']).lower() + " "
                if 'subject' in content:
                    searchable_text += str(content['subject']).lower() + " "
                if 'body' in content:
                    searchable_text += str(content['body']).lower() + " "
            
            # Calculate relevance score
            for term in related_terms:
                term_lower = term.lower()
                if term_lower in searchable_text:
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
                scored_results.append((item, score))
        
        # Sort by relevance score and return top results
        scored_results.sort(key=lambda x: x[1], reverse=True)
        return [item for item, score in scored_results[:limit]]
    
    def get_conversation_by_id(self, conversation_id: str) -> List[Dict]:
        """Get all items for a specific conversation ID"""
        return [item for item in self.conversations 
                if item.get('conversationId') == conversation_id]
    
    def get_customer_conversations(self, customer_id: str) -> List[Dict]:
        """Get all conversations for a specific customer ID"""
        return [item for item in self.conversations 
                if item.get('customerId') == customer_id]
    
    def get_recent_conversations(self, hours: int = 24) -> List[Dict]:
        """Get conversations from the last N hours"""
        if not self.conversations:
            return []
        
        cutoff_time = datetime.now().timestamp() - (hours * 3600)
        recent = []
        
        for item in self.conversations:
            if 'timestamp' in item:
                try:
                    # Parse ISO timestamp
                    item_time = datetime.fromisoformat(item['timestamp'].replace('Z', '+00:00')).timestamp()
                    if item_time >= cutoff_time:
                        recent.append(item)
                except:
                    continue
        
        return recent
    
    def analyze_sentiment(self, conversation_id: str = None) -> Dict[str, Any]:
        """Basic sentiment analysis of conversations"""
        if conversation_id:
            items = self.get_conversation_by_id(conversation_id)
        else:
            items = self.conversations
        
        # Simple keyword-based sentiment analysis
        positive_words = ['good', 'great', 'excellent', 'happy', 'satisfied', 'thank', 'love', 'perfect', 'amazing', 'wonderful']
        negative_words = ['bad', 'terrible', 'awful', 'hate', 'angry', 'frustrated', 'disappointed', 'broken', 'issue', 'problem']
        
        positive_count = 0
        negative_count = 0
        total_messages = 0
        
        for item in items:
            content = item.get('content', {})
            if content.get('type') == 'CHAT_MESSAGE' and 'content' in content:
                text = str(content['content']).lower()
                total_messages += 1
                
                for word in positive_words:
                    if word in text:
                        positive_count += 1
                        break
                
                for word in negative_words:
                    if word in text:
                        negative_count += 1
                        break
        
        return {
            'total_messages': total_messages,
            'positive_messages': positive_count,
            'negative_messages': negative_count,
            'sentiment_score': (positive_count - negative_count) / max(total_messages, 1)
        }


def main():
    parser = argparse.ArgumentParser(description="Claude API Client with Conversation Analysis")
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # Claude API command
    claude_parser = subparsers.add_parser('claude', help='Send message to Claude API')
    claude_parser.add_argument("message", help="Message to send to Claude")
    claude_parser.add_argument("--model", default=CLAUDE_MODEL, help="Claude model to use")
    claude_parser.add_argument("--max-tokens", type=int, default=1000, help="Maximum tokens in response")
    claude_parser.add_argument("--system", help="System prompt")
    claude_parser.add_argument("--stream", action="store_true", help="Stream the response")
    claude_parser.add_argument("--api-key", help="Anthropic API key (or set ANTHROPIC_API_KEY env var)")
    
    # Conversation analysis commands
    conv_parser = subparsers.add_parser('conversations', help='Analyze conversation data')
    conv_parser.add_argument("action", choices=['summary', 'search', 'conversation', 'customer', 'recent', 'sentiment'], 
                           help="Action to perform on conversation data")
    conv_parser.add_argument("--query", help="Search query (for search action)")
    conv_parser.add_argument("--conversation-id", help="Conversation ID (for conversation/sentiment actions)")
    conv_parser.add_argument("--customer-id", help="Customer ID (for customer action)")
    conv_parser.add_argument("--hours", type=int, default=24, help="Hours for recent conversations (default: 24)")
    conv_parser.add_argument("--limit", type=int, default=10, help="Limit number of results (default: 10)")
    conv_parser.add_argument("--jsonl-file", default="conversation_items.jsonl", help="Path to JSONL file")
    
    # Ask Claude about conversations
    ask_parser = subparsers.add_parser('ask', help='Ask Claude about conversation data')
    ask_parser.add_argument("question", help="Question about the conversation data")
    ask_parser.add_argument("--model", default=CLAUDE_MODEL, help="Claude model to use")
    ask_parser.add_argument("--max-tokens", type=int, default=2000, help="Maximum tokens in response")
    ask_parser.add_argument("--api-key", help="Anthropic API key (or set ANTHROPIC_API_KEY env var)")
    ask_parser.add_argument("--jsonl-file", default="conversation_items.jsonl", help="Path to JSONL file")
    
    args = parser.parse_args()
    
    # If no command specified, default to claude
    if not args.command:
        args.command = 'claude'
        # Re-parse with claude as the command
        import sys
        sys.argv = ['claude_api_client.py', 'claude'] + sys.argv[1:]
        args = parser.parse_args()
    
    try:
        if args.command == 'claude':
            client = ClaudeAPIClient(api_key=args.api_key)
            
            if args.stream:
                print("Streaming response:")
                print("-" * 50)
                for chunk in client.stream_message(
                    message=args.message,
                    model=args.model,
                    max_tokens=args.max_tokens,
                    system_prompt=args.system
                ):
                    if 'content' in chunk and chunk['content']:
                        for content_block in chunk['content']:
                            if content_block['type'] == 'text':
                                print(content_block['text'], end='', flush=True)
                print("\n" + "-" * 50)
            else:
                response = client.send_message(
                    message=args.message,
                    model=args.model,
                    max_tokens=args.max_tokens,
                    system_prompt=args.system
                )
                
                print("Response:")
                print("-" * 50)
                if 'content' in response and response['content']:
                    for content_block in response['content']:
                        if content_block['type'] == 'text':
                            print(content_block['text'])
                print("-" * 50)
        
        elif args.command == 'conversations':
            analyzer = ConversationAnalyzer(args.jsonl_file)
            
            if args.action == 'summary':
                print(analyzer.get_conversation_summary())
            
            elif args.action == 'search':
                if not args.query:
                    print("Error: --query is required for search action")
                    sys.exit(1)
                results = analyzer.search_conversations(args.query, args.limit)
                print(f"Found {len(results)} results for query: '{args.query}'")
                print("-" * 50)
                for i, item in enumerate(results, 1):
                    content = item.get('content', {})
                    print(f"{i}. [{item.get('timestamp', 'No timestamp')}] {content.get('type', 'Unknown type')}")
                    if 'content' in content:
                        text = str(content['content'])[:200] + "..." if len(str(content['content'])) > 200 else str(content['content'])
                        print(f"   Content: {text}")
                    print()
            
            elif args.action == 'conversation':
                if not args.conversation_id:
                    print("Error: --conversation-id is required for conversation action")
                    sys.exit(1)
                items = analyzer.get_conversation_by_id(args.conversation_id)
                print(f"Conversation {args.conversation_id} has {len(items)} items:")
                print("-" * 50)
                for item in items:
                    content = item.get('content', {})
                    print(f"[{item.get('timestamp', 'No timestamp')}] {content.get('type', 'Unknown type')}")
                    if 'content' in content:
                        print(f"Content: {content['content']}")
                    print()
            
            elif args.action == 'customer':
                if not args.customer_id:
                    print("Error: --customer-id is required for customer action")
                    sys.exit(1)
                items = analyzer.get_customer_conversations(args.customer_id)
                print(f"Customer {args.customer_id} has {len(items)} conversation items:")
                print("-" * 50)
                for item in items[:args.limit]:
                    content = item.get('content', {})
                    print(f"[{item.get('timestamp', 'No timestamp')}] {content.get('type', 'Unknown type')}")
                    if 'content' in content:
                        text = str(content['content'])[:200] + "..." if len(str(content['content'])) > 200 else str(content['content'])
                        print(f"Content: {text}")
                    print()
            
            elif args.action == 'recent':
                items = analyzer.get_recent_conversations(args.hours)
                print(f"Found {len(items)} conversations from the last {args.hours} hours:")
                print("-" * 50)
                for item in items[:args.limit]:
                    content = item.get('content', {})
                    print(f"[{item.get('timestamp', 'No timestamp')}] {content.get('type', 'Unknown type')}")
                    if 'content' in content:
                        text = str(content['content'])[:200] + "..." if len(str(content['content'])) > 200 else str(content['content'])
                        print(f"Content: {text}")
                    print()
            
            elif args.action == 'sentiment':
                sentiment = analyzer.analyze_sentiment(args.conversation_id)
                print("Sentiment Analysis:")
                print("-" * 50)
                print(f"Total messages: {sentiment['total_messages']}")
                print(f"Positive messages: {sentiment['positive_messages']}")
                print(f"Negative messages: {sentiment['negative_messages']}")
                print(f"Sentiment score: {sentiment['sentiment_score']:.2f}")
                if sentiment['sentiment_score'] > 0.1:
                    print("Overall sentiment: Positive")
                elif sentiment['sentiment_score'] < -0.1:
                    print("Overall sentiment: Negative")
                else:
                    print("Overall sentiment: Neutral")
        
        elif args.command == 'ask':
            analyzer = ConversationAnalyzer(args.jsonl_file)
            client = ClaudeAPIClient(api_key=args.api_key)
            
            # Step 1: Query Planning - Use Claude to understand what data we need
            print("Step 1: Analyzing your question and planning data retrieval...")
            
            query_planning_prompt = f"""You are a data analysis assistant. I have customer support conversation data with the following structure:

Data Types Available:
- CHAT_MESSAGE: Customer and agent chat messages
- EMAIL: Email communications with subjects and content
- CONVERSATION_NOTE: Agent notes and internal documentation
- CONVERSATION_STATUS_CHANGE: Status updates (OPEN/CLOSED)
- PHONE_CALL: Phone call records
- TOPIC_CHANGE: Topic changes in conversations

Each item has: timestamp, customerId, conversationId, and content (which varies by type).

Question: "{args.question}"

Based on this question, provide a JSON response with:
1. "search_terms": List of specific terms to search for in the conversation content
2. "content_types": List of content types to focus on (e.g., ["CHAT_MESSAGE", "EMAIL"])
3. "time_filters": Any time-based filtering needed (e.g., "last_24_hours", "specific_date_range", "all")
4. "analysis_focus": What specific aspects to focus on in the analysis
5. "max_items": Maximum number of conversation items to retrieve (suggest 50-200)

Be specific and comprehensive in your search terms. Think about synonyms, related terms, and different ways the same issue might be expressed.

Respond with valid JSON only."""

            try:
                planning_response = client.send_message(
                    message=query_planning_prompt,
                    model=args.model,
                    max_tokens=500
                )
                
                # Extract JSON from response
                planning_text = planning_response['content'][0]['text']
                # Find JSON in the response
                import re
                json_match = re.search(r'\{.*\}', planning_text, re.DOTALL)
                if json_match:
                    plan = json.loads(json_match.group())
                else:
                    # Fallback to basic plan
                    plan = {
                        "search_terms": [args.question],
                        "content_types": ["CHAT_MESSAGE", "EMAIL", "CONVERSATION_NOTE"],
                        "time_filters": "all",
                        "analysis_focus": "general analysis",
                        "max_items": 100
                    }
                
                print(f"Retrieval plan: {plan['search_terms'][:5]}... (focusing on {plan['content_types']})")
                
            except Exception as e:
                print(f"Query planning failed, using fallback: {e}")
                plan = {
                    "search_terms": [args.question],
                    "content_types": ["CHAT_MESSAGE", "EMAIL", "CONVERSATION_NOTE"],
                    "time_filters": "all",
                    "analysis_focus": "general analysis",
                    "max_items": 100
                }
            
            # Step 2: Data Retrieval - Get relevant conversations based on the plan
            print("Step 2: Retrieving relevant conversation data...")
            
            relevant_data = []
            
            # Search using the planned terms with semantic search
            for term in plan['search_terms']:
                results = analyzer.semantic_search_conversations(term, limit=plan['max_items'] // len(plan['search_terms']))
                relevant_data.extend(results)
            
            # Filter by content types if specified
            if plan['content_types'] != ["all"]:
                relevant_data = [item for item in relevant_data 
                               if item.get('content', {}).get('type') in plan['content_types']]
            
            # Apply time filters if specified
            if plan['time_filters'] == "last_24_hours":
                relevant_data = analyzer.get_recent_conversations(24)
            elif plan['time_filters'] == "last_7_days":
                relevant_data = analyzer.get_recent_conversations(24 * 7)
            
            # Remove duplicates and limit
            seen_ids = set()
            unique_data = []
            for item in relevant_data:
                if item.get('id') not in seen_ids:
                    seen_ids.add(item.get('id'))
                    unique_data.append(item)
                    if len(unique_data) >= plan['max_items']:
                        break
            
            print(f"Retrieved {len(unique_data)} relevant conversation items")
            
            # Step 3: Data Analysis - Send the retrieved data to Claude for analysis
            print("Step 3: Analyzing conversation data with Claude...")
            
            # Get conversation summary for context
            summary = analyzer.get_conversation_summary()
            
            # Format the conversation data for Claude
            conversation_text = "Retrieved Conversation Data:\n\n"
            for i, item in enumerate(unique_data, 1):
                content = item.get('content', {})
                timestamp = item.get('timestamp', 'No timestamp')
                content_type = content.get('type', 'Unknown type')
                customer_id = item.get('customerId', 'Unknown customer')
                conversation_id = item.get('conversationId', 'Unknown conversation')
                
                conversation_text += f"--- Item {i} ---\n"
                conversation_text += f"Type: {content_type}\n"
                conversation_text += f"Timestamp: {timestamp}\n"
                conversation_text += f"Customer: {customer_id}\n"
                conversation_text += f"Conversation: {conversation_id}\n"
                
                # Add content based on type
                if 'content' in content:
                    conversation_text += f"Content: {content['content']}\n"
                if 'subject' in content:
                    conversation_text += f"Subject: {content['subject']}\n"
                if 'body' in content:
                    conversation_text += f"Body: {content['body']}\n"
                
                conversation_text += "\n"
            
            # Create a system prompt with conversation context
            system_prompt = f"""You are analyzing customer support conversation data. Here's a summary of the data:

{summary}

{conversation_text}

Analysis Focus: {plan['analysis_focus']}

Please analyze the conversation data and answer the question: "{args.question}"

Be specific and reference the actual conversation content when possible. Look for patterns, themes, and specific examples in the data. Provide detailed insights based on the retrieved conversations."""
            
            response = client.send_message(
                message=args.question,
                model=args.model,
                max_tokens=args.max_tokens,
                system_prompt=system_prompt
            )
            
            print("\nAnalysis:")
            print("-" * 50)
            if 'content' in response and response['content']:
                for content_block in response['content']:
                    if content_block['type'] == 'text':
                        print(content_block['text'])
            print("-" * 50)
    
    except Exception as e:
        print(f"Error: {e}")
        import sys
        sys.exit(1)


if __name__ == "__main__":
    main()
