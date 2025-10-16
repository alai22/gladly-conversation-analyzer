#!/usr/bin/env python3
"""
Setup script for Claude API Client
"""

import os
import shutil

def setup_config():
    """Set up configuration files"""
    print("🔧 Setting up Claude API Client...")
    
    # Check if config_local.py exists
    if os.path.exists('config_local.py'):
        print("✅ config_local.py already exists")
    else:
        # Copy config.py to config_local.py
        shutil.copy('config.py', 'config_local.py')
        print("📝 Created config_local.py from config.py")
        print("⚠️  Please edit config_local.py and add your actual API key!")
    
    # Check if conversation data exists
    if os.path.exists('conversation_items.jsonl'):
        print("✅ conversation_items.jsonl found")
    else:
        print("⚠️  conversation_items.jsonl not found - conversation analysis features won't work")
    
    print("\n📋 Next steps:")
    print("1. Edit config_local.py and add your Anthropic API key")
    print("2. Run: python3 test_commands.py")
    print("3. Or run individual commands like:")
    print("   python3 claude_api_client.py 'Hello, Claude!'")
    print("   python3 claude_api_client.py ask 'What are the main customer complaints?'")

if __name__ == "__main__":
    setup_config()

