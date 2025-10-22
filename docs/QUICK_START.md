# 🚀 Quick Start Guide

## 1. Setup (30 seconds)

```bash
# Run setup script
python3 setup.py

# Edit config_local.py and add your API key
# Replace 'your-api-key-here' with your actual Anthropic API key
```

## 2. Test Basic Functionality

```bash
# Test conversation analysis (no API key needed)
python3 claude_api_client.py conversations summary

# Test Claude API (needs API key)
python3 claude_api_client.py "Hello, Claude!"
```

## 3. Try RAG System

```bash
# Ask Claude about your conversation data
python3 claude_api_client.py ask "What are the main customer complaints?"

# Ask about specific topics
python3 claude_api_client.py ask "What quality issues do customers mention?"
python3 claude_api_client.py ask "How many refund requests were there?"
```

## 4. Run All Tests

```bash
python3 test_commands.py
```

## 📁 File Structure

- `claude_api_client.py` - Main script
- `config_local.py` - Your API key (edit this!)
- `conversation_items.jsonl` - Your conversation data
- `test_commands.py` - Test script
- `EXAMPLES.md` - Detailed examples

## 🔑 API Key Setup

1. Get your API key from [Anthropic Console](https://console.anthropic.com/)
2. Edit `config_local.py`
3. Replace `your-api-key-here` with your actual key
4. Save the file

## 🎯 What You Can Do

### Basic Claude API
- Chat with Claude
- Ask questions
- Get creative content
- Stream responses

### Conversation Analysis
- Search conversations
- Get data summaries
- Analyze sentiment
- Track customer history

### RAG System
- Ask intelligent questions about your data
- Get AI-powered insights
- Find patterns and trends
- Analyze customer feedback

## 🆘 Need Help?

- Check `EXAMPLES.md` for detailed examples
- Run `python3 claude_api_client.py --help` for command help
- Make sure your API key is set in `config_local.py`

