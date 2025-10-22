# Claude API Client with Conversation Analysis

A Python script to interact with the Claude API and analyze customer support conversation data from your local machine.

## Setup

1. Install dependencies:
   ```bash
   python3 -m pip install -r requirements.txt
   ```

2. Get your Anthropic API key from [Anthropic Console](https://console.anthropic.com/)

3. Set your API key as an environment variable:
   ```bash
   export ANTHROPIC_API_KEY="your-api-key-here"
   ```

## Usage

The script now supports three main modes:

### 1. Claude API (Original Functionality)
```bash
# Basic usage (default mode)
python3 claude_api_client.py "Hello, Claude!"

# With custom model
python3 claude_api_client.py "Explain quantum computing" --model claude-3-5-sonnet-20241022

# With system prompt
python3 claude_api_client.py "Write a poem" --system "You are a creative poet who writes in haiku format"

# Streaming response
python3 claude_api_client.py "Tell me a long story" --stream

# Explicit claude command
python3 claude_api_client.py claude "Hello, Claude!"
```

### 2. Conversation Analysis
```bash
# Get summary of conversation data
python3 claude_api_client.py conversations summary

# Search conversations
python3 claude_api_client.py conversations search --query "refund"

# Get specific conversation
python3 claude_api_client.py conversations conversation --conversation-id "vhGOxHmTRtmKJg1Ik0lpYQ"

# Get customer conversations
python3 claude_api_client.py conversations customer --customer-id "U6348-Q7QFOREwXT8kR3zg"

# Get recent conversations (last 24 hours)
python3 claude_api_client.py conversations recent --hours 48

# Analyze sentiment
python3 claude_api_client.py conversations sentiment --conversation-id "vhGOxHmTRtmKJg1Ik0lpYQ"
```

### 3. Ask Claude About Conversations (RAG System)
```bash
# Ask Claude to analyze your conversation data with intelligent retrieval
python3 claude_api_client.py ask "What are the main customer complaints?"

# Ask specific questions about product quality
python3 claude_api_client.py ask "What quality issues do customers mention most?"

# Ask about customer satisfaction patterns
python3 claude_api_client.py ask "What patterns do you see in customer satisfaction?"

# Ask about specific topics
python3 claude_api_client.py ask "How many customers have issues with GPS tracking?"

# Ask about refund patterns
python3 claude_api_client.py ask "What are the main reasons customers request refunds?"
```

**RAG System Features:**
- **Intelligent Query Planning**: Claude interprets your question and creates a retrieval plan
- **Semantic Search**: Finds related concepts and synonyms automatically
- **Contextual Retrieval**: Gets the most relevant conversation data based on your question
- **Focused Analysis**: Claude receives targeted data for better insights

### Using as a Python Module
```python
from claude_api_client import ClaudeAPIClient, ConversationAnalyzer

# Claude API usage
client = ClaudeAPIClient()

# Simple message
response = client.send_message("Hello, Claude!")
print(response['content'][0]['text'])

# With system prompt
response = client.send_message(
    "Write a haiku about coding",
    system_prompt="You are a creative poet"
)
print(response['content'][0]['text'])

# Streaming
for chunk in client.stream_message("Tell me a story"):
    if 'content' in chunk and chunk['content']:
        for content_block in chunk['content']:
            if content_block['type'] == 'text':
                print(content_block['text'], end='', flush=True)

# Conversation analysis
analyzer = ConversationAnalyzer("conversation_items.jsonl")

# Get summary
summary = analyzer.get_conversation_summary()
print(summary)

# Search conversations
results = analyzer.search_conversations("refund", limit=5)
for result in results:
    print(f"Found: {result['content']['content'][:100]}...")

# Get specific conversation
conversation = analyzer.get_conversation_by_id("vhGOxHmTRtmKJg1Ik0lpYQ")
print(f"Conversation has {len(conversation)} items")

# Analyze sentiment
sentiment = analyzer.analyze_sentiment()
print(f"Overall sentiment score: {sentiment['sentiment_score']}")
```

## Security Notes

- **No tunneling required**: This script runs locally and makes direct HTTPS calls to Anthropic's API
- **API key security**: Store your API key in environment variables, not in the code
- **HTTPS encryption**: All communication is encrypted via HTTPS
- **Rate limiting**: Anthropic has rate limits, so be mindful of usage

## Available Models

- `claude-3-5-sonnet-20241022` (most capable, default)
- `claude-3-5-haiku-20241022` (fastest, cheapest)
- `claude-3-opus-20240229` (legacy, most capable)

## Conversation Data Features

The script can analyze customer support conversation data from `conversation_items.jsonl`:

### Data Types Supported
- **CHAT_MESSAGE**: Customer and agent chat messages
- **EMAIL**: Email communications
- **CONVERSATION_NOTE**: Agent notes and internal documentation
- **CONVERSATION_STATUS_CHANGE**: Status updates (OPEN/CLOSED)

### Analysis Capabilities
- **Summary**: Overview of data volume, types, and date ranges
- **Search**: Full-text search across all conversation content
- **Conversation Tracking**: Follow specific conversation threads
- **Customer History**: View all interactions for a specific customer
- **Recent Activity**: Filter conversations by time
- **Sentiment Analysis**: Basic sentiment scoring of messages
- **AI-Powered Insights**: Ask Claude to analyze patterns and trends

### Data Privacy
- All data processing happens locally
- No conversation data is sent to external services (except when using the 'ask' command)
- Original data files remain unchanged

## Error Handling

The script includes proper error handling for:
- Missing API key
- Network errors
- API rate limits
- Invalid responses
- Missing conversation data files
- Malformed JSON data
