#!/usr/bin/env python3
"""
Test with known working conversation IDs

This script tests the API with conversation IDs that we know exist
in the existing conversation data.
"""

import os
import json
import requests
import logging
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_known_conversation_ids():
    """Test with conversation IDs that we know exist in the data"""
    
    api_key = os.getenv('GLADLY_API_KEY')
    
    if not api_key:
        logger.error("GLADLY_API_KEY environment variable not set")
        return False
    
    # These are conversation IDs that exist in our current data
    known_conversation_ids = [
        "vhGOxHmTRtmKJg1Ik0lpYQ",
        "cksmMJtUSq-Bi-kQW2xWRg",
        "XYYjBCtuQoadsITX9k_P9w"
    ]
    
    base_url = "https://halocollar.us-1.gladly.com"
    
    # Test different endpoints and auth methods
    endpoints = [
        f"/conversations/{{id}}/items",
        f"/api/v1/conversations/{{id}}/items",
        f"/api/conversations/{{id}}/items"
    ]
    
    auth_methods = [
        {'name': 'Bearer', 'headers': {'Authorization': f'Bearer {api_key}'}},
        {'name': 'API-Key', 'headers': {'API-Key': api_key}},
        {'name': 'X-API-Key', 'headers': {'X-API-Key': api_key}},
    ]
    
    for conversation_id in known_conversation_ids:
        logger.info(f"\nTesting conversation ID: {conversation_id}")
        
        for endpoint_template in endpoints:
            endpoint = endpoint_template.format(id=conversation_id)
            
            for auth_method in auth_methods:
                url = f"{base_url}{endpoint}"
                headers = {
                    'Content-Type': 'application/json',
                    'Accept': 'application/json',
                    **auth_method['headers']
                }
                
                try:
                    logger.info(f"  Testing: {auth_method['name']} + {endpoint}")
                    response = requests.get(url, headers=headers, timeout=10)
                    
                    logger.info(f"    Status: {response.status_code}")
                    logger.info(f"    Content-Type: {response.headers.get('content-type', 'unknown')}")
                    
                    if response.status_code == 200:
                        if 'application/json' in response.headers.get('content-type', ''):
                            logger.info(f"    [SUCCESS] Got JSON response!")
                            try:
                                data = response.json()
                                logger.info(f"    Data keys: {list(data.keys()) if isinstance(data, dict) else 'Not a dict'}")
                                if isinstance(data, dict) and 'items' in data:
                                    logger.info(f"    Items count: {len(data['items'])}")
                                return True
                            except Exception as e:
                                logger.error(f"    [ERROR] Invalid JSON: {e}")
                        else:
                            logger.warning(f"    [WARNING] Got non-JSON response")
                            logger.info(f"    Response preview: {response.text[:100]}...")
                    else:
                        logger.info(f"    Response: {response.text[:100]}...")
                        
                except requests.exceptions.RequestException as e:
                    logger.error(f"    Error: {e}")
    
    return False

if __name__ == "__main__":
    test_known_conversation_ids()
