#!/usr/bin/env python3
"""
Advanced test script for Gladly API authentication

This script tests different authentication methods and API endpoints
to determine the correct way to access the Gladly API.
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

def test_api_endpoints():
    """Test different API endpoints and authentication methods"""
    
    api_key = os.getenv('GLADLY_API_KEY')
    
    if not api_key:
        logger.error("GLADLY_API_KEY environment variable not set")
        return False
    
    base_url = "https://halocollar.us-1.gladly.com"
    test_conversation_id = "--2OW1qWSLyJTXeZ0XA2dA"
    
    # Different authentication methods to try
    auth_methods = [
        {
            'name': 'Bearer Token',
            'headers': {
                'Authorization': f'Bearer {api_key}',
                'Content-Type': 'application/json',
                'Accept': 'application/json'
            }
        },
        {
            'name': 'API Key Header',
            'headers': {
                'X-API-Key': api_key,
                'Content-Type': 'application/json',
                'Accept': 'application/json'
            }
        },
        {
            'name': 'Authorization Header',
            'headers': {
                'Authorization': api_key,
                'Content-Type': 'application/json',
                'Accept': 'application/json'
            }
        },
        {
            'name': 'Gladly API Key',
            'headers': {
                'Gladly-API-Key': api_key,
                'Content-Type': 'application/json',
                'Accept': 'application/json'
            }
        }
    ]
    
    # Different endpoints to try
    endpoints = [
        f"/api/v1/conversations/{test_conversation_id}/items",
        f"/api/conversations/{test_conversation_id}/items",
        f"/conversations/{test_conversation_id}/items",
        f"/api/v1/conversation/{test_conversation_id}/items",
        f"/api/v1/conversations/{test_conversation_id}",
        f"/api/conversations/{test_conversation_id}",
        f"/conversations/{test_conversation_id}"
    ]
    
    results = []
    
    for auth_method in auth_methods:
        logger.info(f"\nTesting authentication method: {auth_method['name']}")
        
        for endpoint in endpoints:
            url = f"{base_url}{endpoint}"
            logger.info(f"  Testing endpoint: {endpoint}")
            
            try:
                response = requests.get(url, headers=auth_method['headers'], timeout=10)
                
                result = {
                    'auth_method': auth_method['name'],
                    'endpoint': endpoint,
                    'url': url,
                    'status_code': response.status_code,
                    'success': response.status_code == 200,
                    'response_preview': response.text[:200] if response.text else 'No response body'
                }
                
                if response.status_code == 200:
                    logger.info(f"    [SUCCESS] Status: {response.status_code}")
                    try:
                        data = response.json()
                        result['data_structure'] = list(data.keys()) if isinstance(data, dict) else 'Not a dict'
                        logger.info(f"    Data keys: {result['data_structure']}")
                    except:
                        result['data_structure'] = 'Invalid JSON'
                elif response.status_code == 401:
                    logger.warning(f"    [AUTH ERROR] Status: {response.status_code}")
                elif response.status_code == 404:
                    logger.info(f"    [NOT FOUND] Status: {response.status_code}")
                else:
                    logger.info(f"    [OTHER] Status: {response.status_code}")
                
                results.append(result)
                
            except requests.exceptions.RequestException as e:
                logger.error(f"    [ERROR] Request failed: {e}")
                results.append({
                    'auth_method': auth_method['name'],
                    'endpoint': endpoint,
                    'url': url,
                    'status_code': 'ERROR',
                    'success': False,
                    'error': str(e)
                })
    
    # Save results
    with open('api_test_results.json', 'w') as f:
        json.dump(results, f, indent=2)
    
    # Find successful combinations
    successful = [r for r in results if r.get('success', False)]
    
    logger.info(f"\n=== SUMMARY ===")
    logger.info(f"Total tests: {len(results)}")
    logger.info(f"Successful: {len(successful)}")
    
    if successful:
        logger.info(f"\n[SUCCESS] Working combinations found:")
        for result in successful:
            logger.info(f"  - Auth: {result['auth_method']}")
            logger.info(f"  - Endpoint: {result['endpoint']}")
            logger.info(f"  - Status: {result['status_code']}")
    else:
        logger.error(f"\n[ERROR] No successful API calls found")
        logger.error(f"Please check:")
        logger.error(f"  1. API key is correct")
        logger.error(f"  2. API key has proper permissions")
        logger.error(f"  3. Conversation ID format is correct")
        logger.error(f"  4. API endpoint URL is correct")
    
    logger.info(f"\nDetailed results saved to: api_test_results.json")
    return len(successful) > 0

if __name__ == "__main__":
    test_api_endpoints()
