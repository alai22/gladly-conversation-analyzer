#!/usr/bin/env python3
"""
Test script for Gladly Conversation Downloader

This script tests the downloader with a few conversation IDs to verify
the API connection and data format before downloading all conversations.
"""

import os
import json
from gladly_downloader import GladlyDownloader
import logging
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_downloader():
    """Test the downloader with a few conversation IDs"""
    
    # Get API key and agent email from environment variables
    api_key = os.getenv('GLADLY_API_KEY')
    agent_email = os.getenv('GLADLY_AGENT_EMAIL')
    
    if not api_key:
        logger.error("GLADLY_API_KEY environment variable not set")
        logger.error("Please set your Gladly API key: export GLADLY_API_KEY=your_api_key")
        return False
    
    if not agent_email:
        logger.error("GLADLY_AGENT_EMAIL environment variable not set")
        logger.error("Please set your agent email: export GLADLY_AGENT_EMAIL=your.email@halocollar.com")
        return False
    
    # Test conversation IDs from the CSV (first few)
    test_conversation_ids = [
        "--2OW1qWSLyJTXeZ0XA2dA",
        "--JgNh67TE2SItqZb_MOyQ", 
        "--Jh7KvATvWjnIKk1KT_VQ"
    ]
    
    # Initialize downloader
    downloader = GladlyDownloader(api_key, agent_email)
    
    logger.info("Testing Gladly API connection with sample conversation IDs...")
    
    successful_downloads = 0
    test_results = []
    
    for conversation_id in test_conversation_ids:
        logger.info(f"Testing conversation ID: {conversation_id}")
        
        conversation_data = downloader.download_conversation_items(conversation_id)
        
        if conversation_data:
            successful_downloads += 1
            logger.info(f"[SUCCESS] Successfully downloaded conversation {conversation_id}")
            logger.info(f"  - Items count: {len(conversation_data.get('items', []))}")
            
            # Store test result
            test_results.append({
                'conversation_id': conversation_id,
                'status': 'success',
                'items_count': len(conversation_data.get('items', [])),
                'data_preview': conversation_data.get('items', [])[:2] if conversation_data.get('items') else []
            })
        else:
            logger.warning(f"[FAILED] Failed to download conversation {conversation_id}")
            test_results.append({
                'conversation_id': conversation_id,
                'status': 'failed',
                'error': 'Download failed'
            })
    
    # Save test results
    with open('test_results.json', 'w') as f:
        json.dump(test_results, f, indent=2)
    
    logger.info(f"\nTest Results:")
    logger.info(f"Successful downloads: {successful_downloads}/{len(test_conversation_ids)}")
    logger.info(f"Test results saved to: test_results.json")
    
    if successful_downloads > 0:
        logger.info("[SUCCESS] API connection successful! Ready to download all conversations.")
        return True
    else:
        logger.error("[ERROR] All test downloads failed. Please check your API key and network connection.")
        return False

if __name__ == "__main__":
    test_downloader()
