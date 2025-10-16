# Claude API Client - Example Commands

## 🚀 Quick Setup

1. **Set up your API key:**
   ```bash
   python3 setup.py
   # Edit config_local.py and add your API key
   ```

2. **Test everything:**
   ```bash
   python3 test_commands.py
   ```

## 📝 Example Commands

### Basic Claude API Commands

```bash
# Simple conversation
python3 claude_api_client.py "Hello, Claude! Tell me a joke."

# With custom model
python3 claude_api_client.py "Explain quantum computing" --model claude-3-5-haiku-20241022

# With system prompt
python3 claude_api_client.py "Write a poem" --system "You are a creative poet"

# Streaming response
python3 claude_api_client.py "Tell me a long story" --stream

# Custom token limit
python3 claude_api_client.py "Summarize the history of AI" --max-tokens 2000
```

### Conversation Analysis Commands

```bash
# Get data summary
python3 claude_api_client.py conversations summary

# Search for specific terms
python3 claude_api_client.py conversations search --query "refund"
python3 claude_api_client.py conversations search --query "GPS" --limit 10

# Get recent conversations
python3 claude_api_client.py conversations recent --hours 24
python3 claude_api_client.py conversations recent --hours 168 --limit 20

# Analyze specific conversation
python3 claude_api_client.py conversations conversation --conversation-id "vhGOxHmTRtmKJg1Ik0lpYQ"

# Get customer history
python3 claude_api_client.py conversations customer --customer-id "U6348-Q7QFOREwXT8kR3zg"

# Sentiment analysis
python3 claude_api_client.py conversations sentiment
python3 claude_api_client.py conversations sentiment --conversation-id "vhGOxHmTRtmKJg1Ik0lpYQ"
```

### RAG System Commands (Ask Claude About Data)

```bash
# General analysis questions
python3 claude_api_client.py ask "What are the main customer complaints?"
python3 claude_api_client.py ask "What patterns do you see in customer satisfaction?"

# Product-specific questions
python3 claude_api_client.py ask "What quality issues do customers mention most?"
python3 claude_api_client.py ask "How many customers have GPS tracking problems?"
python3 claude_api_client.py ask "What battery problems do customers experience?"

# Service-related questions
python3 claude_api_client.py ask "What are the main reasons for refund requests?"
python3 claude_api_client.py ask "What shipping issues do customers report?"
python3 claude_api_client.py ask "How do customers feel about the Halo collar app?"

# Customer experience questions
python3 claude_api_client.py ask "What are customers saying about customer service?"
python3 claude_api_client.py ask "What safety concerns do customers have?"
python3 claude_api_client.py ask "What features do customers love most?"

# Technical questions
python3 claude_api_client.py ask "What technical problems do customers report?"
python3 claude_api_client.py ask "How often do customers mention app crashes?"
python3 claude_api_client.py ask "What connectivity issues do customers face?"

# Business insights
python3 claude_api_client.py ask "What trends do you see in customer feedback?"
python3 claude_api_client.py ask "What improvements do customers suggest?"
python3 claude_api_client.py ask "How has customer satisfaction changed over time?"
```

### Advanced RAG Commands

```bash
# With custom model
python3 claude_api_client.py ask "Analyze customer sentiment" --model claude-3-5-haiku-20241022

# With more tokens for detailed analysis
python3 claude_api_client.py ask "Provide a comprehensive analysis of customer complaints" --max-tokens 4000

# With custom conversation file
python3 claude_api_client.py ask "What are the main issues?" --jsonl-file "other_conversations.jsonl"
```

## 🔧 Configuration

### API Key Setup
The script looks for your API key in this order:
1. `config_local.py` (recommended)
2. `config.py` (fallback)
3. `ANTHROPIC_API_KEY` environment variable

### Model Options
- `claude-3-5-sonnet-20241022` (default, most capable)
- `claude-3-5-haiku-20241022` (fastest, cheapest)
- `claude-3-opus-20240229` (legacy, most capable)

### File Structure
```
gladly/
├── claude_api_client.py      # Main script
├── config.py                 # Default configuration
├── config_local.py           # Your local config (add API key here)
├── conversation_items.jsonl  # Your conversation data
├── test_commands.py          # Test script
├── setup.py                  # Setup script
└── .gitignore               # Protects your API key
```

## 🧪 Testing

### Run All Tests
```bash
python3 test_commands.py
```

### Test Individual Features
```bash
# Test basic Claude API
python3 claude_api_client.py "Hello, Claude!"

# Test conversation analysis
python3 claude_api_client.py conversations summary

# Test RAG system
python3 claude_api_client.py ask "What are the main customer complaints?"
```

## 💡 Tips

1. **Start with simple questions** to test the RAG system
2. **Use specific terms** in your questions for better results
3. **Try different models** for different use cases
4. **Check the conversation summary** first to understand your data
5. **Use the search feature** to find specific conversations before asking Claude

## 🚨 Troubleshooting

### API Key Issues
```bash
# Check if config file exists
ls -la config_local.py

# Verify API key is set
python3 -c "from config_local import ANTHROPIC_API_KEY; print('API key set:', ANTHROPIC_API_KEY != 'your-api-key-here')"
```

### Data Issues
```bash
# Check if conversation data exists
ls -la conversation_items.jsonl

# Test data loading
python3 claude_api_client.py conversations summary
```

### Model Issues
```bash
# Test with different model
python3 claude_api_client.py "Hello" --model claude-3-5-haiku-20241022
```

