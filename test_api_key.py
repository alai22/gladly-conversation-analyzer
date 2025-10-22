#!/usr/bin/env python3
"""
Simple API key validation test

This script tests if the API key is being loaded correctly and tries
to understand the authentication requirements.
"""

import os
import requests
import logging
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_api_key():
    """Test API key loading and basic authentication"""
    
    api_key = os.getenv('GLADLY_API_KEY')
    
    if not api_key:
        logger.error("GLADLY_API_KEY environment variable not set")
        return False
    
    logger.info(f"API key loaded: {api_key[:10]}...{api_key[-4:] if len(api_key) > 14 else '***'}")
    logger.info(f"API key length: {len(api_key)}")
    
    # Test a simple endpoint that might not require authentication
    base_url = "https://halocollar.us-1.gladly.com"
    
    # Try to access a basic endpoint
    test_urls = [
        f"{base_url}/api/health",
        f"{base_url}/health",
        f"{base_url}/api/v1/health",
        f"{base_url}/api/v1/status",
        f"{base_url}/status"
    ]
    
    for url in test_urls:
        try:
            logger.info(f"Testing: {url}")
            response = requests.get(url, timeout=10)
            logger.info(f"  Status: {response.status_code}")
            logger.info(f"  Content-Type: {response.headers.get('content-type', 'unknown')}")
            logger.info(f"  Response length: {len(response.text)}")
            
            if response.status_code == 200:
                logger.info(f"  Response preview: {response.text[:100]}...")
            
        except requests.exceptions.RequestException as e:
            logger.error(f"  Error: {e}")
    
    # Test with authentication
    logger.info(f"\nTesting with authentication...")
    test_conversation_id = "--2OW1qWSLyJTXeZ0XA2dA"
    
    auth_methods = [
        {'name': 'Bearer', 'headers': {'Authorization': f'Bearer {api_key}'}},
        {'name': 'API-Key', 'headers': {'API-Key': api_key}},
        {'name': 'X-API-Key', 'headers': {'X-API-Key': api_key}},
        {'name': 'Authorization', 'headers': {'Authorization': api_key}},
    ]
    
    for auth_method in auth_methods:
        url = f"{base_url}/conversations/{test_conversation_id}/items"
        headers = {
            'Content-Type': 'application/json',
            'Accept': 'application/json',
            **auth_method['headers']
        }
        
        try:
            logger.info(f"Testing {auth_method['name']} auth...")
            response = requests.get(url, headers=headers, timeout=10)
            logger.info(f"  Status: {response.status_code}")
            logger.info(f"  Content-Type: {response.headers.get('content-type', 'unknown')}")
            
            if response.status_code == 200:
                if 'application/json' in response.headers.get('content-type', ''):
                    logger.info(f"  [SUCCESS] Got JSON response!")
                    try:
                        data = response.json()
                        logger.info(f"  Data keys: {list(data.keys()) if isinstance(data, dict) else 'Not a dict'}")
                        return True
                    except:
                        logger.error(f"  [ERROR] Invalid JSON")
                else:
                    logger.warning(f"  [WARNING] Got non-JSON response")
                    logger.info(f"  Response preview: {response.text[:100]}...")
            else:
                logger.info(f"  Response: {response.text[:100]}...")
                
        except requests.exceptions.RequestException as e:
            logger.error(f"  Error: {e}")
    
    return False

if __name__ == "__main__":
    test_api_key()
