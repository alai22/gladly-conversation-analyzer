#!/usr/bin/env python3
"""
Example test commands for the Claude API Client with RAG system
"""

import subprocess
import sys

def run_command(cmd):
    """Run a command and print the result"""
    print(f"\n{'='*80}")
    print(f"Running: {cmd}")
    print('='*80)
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        print("STDOUT:")
        print(result.stdout)
        if result.stderr:
            print("STDERR:")
            print(result.stderr)
        return result.returncode == 0
    except Exception as e:
        print(f"Error running command: {e}")
        return False

def test_basic_claude():
    """Test basic Claude API functionality"""
    print("\n🧠 Testing Basic Claude API...")
    
    commands = [
        'python3 claude_api_client.py "Hello, Claude! Can you tell me a short joke?"',
        'python3 claude_api_client.py "Explain quantum computing in simple terms" --max-tokens 500',
        'python3 claude_api_client.py "Write a haiku about coding" --system "You are a creative poet"'
    ]
    
    for cmd in commands:
        run_command(cmd)

def test_conversation_analysis():
    """Test conversation analysis features"""
    print("\n📊 Testing Conversation Analysis...")
    
    commands = [
        'python3 claude_api_client.py conversations summary',
        'python3 claude_api_client.py conversations search --query "refund" --limit 5',
        'python3 claude_api_client.py conversations recent --hours 24 --limit 3',
        'python3 claude_api_client.py conversations sentiment'
    ]
    
    for cmd in commands:
        run_command(cmd)

def test_rag_system():
    """Test RAG system with various questions"""
    print("\n🔍 Testing RAG System...")
    
    questions = [
        "What are the main customer complaints?",
        "What quality issues do customers mention most?",
        "How many customers have GPS tracking problems?",
        "What are the main reasons for refund requests?",
        "What patterns do you see in customer satisfaction?",
        "What shipping issues do customers report?",
        "How do customers feel about the Halo collar app?",
        "What battery problems do customers experience?"
    ]
    
    for question in questions:
        cmd = f'python3 claude_api_client.py ask "{question}"'
        run_command(cmd)

def test_specific_conversations():
    """Test specific conversation analysis"""
    print("\n🎯 Testing Specific Conversation Analysis...")
    
    # First get some conversation IDs
    print("Getting sample conversation IDs...")
    result = subprocess.run('python3 claude_api_client.py conversations search --query "refund" --limit 1', 
                          shell=True, capture_output=True, text=True)
    
    # Extract conversation ID from output (this is a simplified approach)
    # In practice, you'd parse the output to get actual conversation IDs
    commands = [
        'python3 claude_api_client.py conversations conversation --conversation-id "vhGOxHmTRtmKJg1Ik0lpYQ"',
        'python3 claude_api_client.py conversations customer --customer-id "U6348-Q7QFOREwXT8kR3zg" --limit 3'
    ]
    
    for cmd in commands:
        run_command(cmd)

def main():
    """Run all tests"""
    print("🚀 Starting Claude API Client Tests")
    print("Make sure you have set your API key in config_local.py first!")
    
    # Check if config_local.py exists
    try:
        with open('config_local.py', 'r') as f:
            content = f.read()
            if 'your-api-key-here' in content:
                print("\n⚠️  WARNING: Please update config_local.py with your actual API key!")
                print("Edit config_local.py and replace 'your-api-key-here' with your real API key.")
                return
    except FileNotFoundError:
        print("\n⚠️  WARNING: config_local.py not found!")
        print("Copy config.py to config_local.py and add your API key.")
        return
    
    # Run tests
    test_basic_claude()
    test_conversation_analysis()
    test_rag_system()
    test_specific_conversations()
    
    print("\n✅ All tests completed!")

if __name__ == "__main__":
    main()

