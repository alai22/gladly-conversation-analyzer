#!/usr/bin/env python3
"""
Gladly Conversation Downloader

This script downloads conversation items from the Gladly API using conversation IDs
from the CSV file 'data/conversation_metrics.csv'.
"""

import csv
import json
import os
import time
import requests
from typing import List, Dict, Optional
from datetime import datetime
import logging
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('gladly_download.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class GladlyDownloader:
    """Downloads conversation items from Gladly API"""
    
    def __init__(self, api_key: str, agent_email: str, base_url: str = "https://halocollar.us-1.gladly.com"):
        self.api_key = api_key
        self.agent_email = agent_email
        self.base_url = base_url
        self.session = requests.Session()
        # Gladly uses Basic Auth with email as username and API token as password
        self.session.auth = (agent_email, api_key)
        self.session.headers.update({
            'Content-Type': 'application/json',
            'Accept': 'application/json',
            'User-Agent': 'Gladly-Conversation-Analyzer/1.0'
        })
        
    def download_conversation_items(self, conversation_id: str) -> Optional[Dict]:
        """Download conversation items for a specific conversation ID"""
        url = f"{self.base_url}/api/v1/conversations/{conversation_id}/items"
        
        try:
            logger.info(f"Downloading conversation items for ID: {conversation_id}")
            response = self.session.get(url, timeout=30)
            
            if response.status_code == 200:
                logger.info(f"Response content type: {response.headers.get('content-type', 'unknown')}")
                logger.info(f"Response length: {len(response.text)}")
                
                if not response.text.strip():
                    logger.warning(f"Empty response for conversation {conversation_id}")
                    return None
                
                try:
                    data = response.json()
                    # The API returns a list of items directly
                    if isinstance(data, list):
                        logger.info(f"Successfully downloaded {len(data)} items for conversation {conversation_id}")
                        return {'items': data}  # Wrap in object for consistency
                    else:
                        logger.info(f"Successfully downloaded {len(data.get('items', []))} items for conversation {conversation_id}")
                        return data
                except json.JSONDecodeError as e:
                    logger.error(f"JSON decode error for conversation {conversation_id}: {e}")
                    logger.error(f"Response content: {response.text[:500]}...")
                    return None
            elif response.status_code == 404:
                logger.warning(f"Conversation {conversation_id} not found (404)")
                return None
            elif response.status_code == 401:
                logger.error(f"Unauthorized access for conversation {conversation_id} (401)")
                return None
            else:
                logger.error(f"Failed to download conversation {conversation_id}: HTTP {response.status_code}")
                logger.error(f"Response: {response.text}")
                return None
                
        except requests.exceptions.RequestException as e:
            logger.error(f"Request error for conversation {conversation_id}: {e}")
            return None
    
    def read_conversation_ids_from_csv(self, csv_file: str) -> List[str]:
        """Read conversation IDs from the CSV file"""
        conversation_ids = []
        
        try:
            with open(csv_file, 'r', encoding='utf-8') as file:
                reader = csv.DictReader(file)
                for row in reader:
                    conversation_id = row.get('Conversation ID', '').strip()
                    if conversation_id and conversation_id != '':
                        conversation_ids.append(conversation_id)
            
            logger.info(f"Found {len(conversation_ids)} conversation IDs in CSV file")
            return conversation_ids
            
        except FileNotFoundError:
            logger.error(f"CSV file not found: {csv_file}")
            return []
        except Exception as e:
            logger.error(f"Error reading CSV file: {e}")
            return []
    
    def download_all_conversations(self, csv_file: str, output_file: str = None, 
                                 batch_size: int = 100, delay: float = 0.1):
        """Download all conversations from CSV file"""
        conversation_ids = self.read_conversation_ids_from_csv(csv_file)
        
        if not conversation_ids:
            logger.error("No conversation IDs found in CSV file")
            return
        
        if output_file is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_file = f"gladly_conversations_{timestamp}.jsonl"
        
        downloaded_count = 0
        failed_count = 0
        
        logger.info(f"Starting download of {len(conversation_ids)} conversations")
        logger.info(f"Output file: {output_file}")
        
        with open(output_file, 'w', encoding='utf-8') as outfile:
            for i, conversation_id in enumerate(conversation_ids, 1):
                logger.info(f"Processing conversation {i}/{len(conversation_ids)}: {conversation_id}")
                
                conversation_data = self.download_conversation_items(conversation_id)
                
                if conversation_data:
                    # Add metadata
                    conversation_data['_metadata'] = {
                        'conversation_id': conversation_id,
                        'downloaded_at': datetime.now().isoformat(),
                        'batch_number': i
                    }
                    
                    # Write to JSONL file
                    outfile.write(json.dumps(conversation_data) + '\n')
                    downloaded_count += 1
                else:
                    failed_count += 1
                
                # Add delay to avoid rate limiting
                if delay > 0:
                    time.sleep(delay)
                
                # Log progress every batch_size
                if i % batch_size == 0:
                    logger.info(f"Progress: {i}/{len(conversation_ids)} conversations processed")
        
        logger.info(f"Download completed!")
        logger.info(f"Successfully downloaded: {downloaded_count}")
        logger.info(f"Failed downloads: {failed_count}")
        logger.info(f"Output saved to: {output_file}")

def main():
    """Main function"""
    # Get API key and agent email from environment variables
    api_key = os.getenv('GLADLY_API_KEY')
    agent_email = os.getenv('GLADLY_AGENT_EMAIL')
    
    if not api_key:
        logger.error("GLADLY_API_KEY environment variable not set")
        logger.error("Please set your Gladly API key: export GLADLY_API_KEY=your_api_key")
        return
    
    if not agent_email:
        logger.error("GLADLY_AGENT_EMAIL environment variable not set")
        logger.error("Please set your agent email: export GLADLY_AGENT_EMAIL=your.email@halocollar.com")
        return
    
    # Configuration
    csv_file = "data/conversation_metrics.csv"
    
    # Initialize downloader
    downloader = GladlyDownloader(api_key, agent_email)
    
    # Download all conversations
    downloader.download_all_conversations(
        csv_file=csv_file,
        output_file="gladly_conversations_downloaded.jsonl",
        batch_size=50,  # Log progress every 50 downloads
        delay=0.1  # 100ms delay between requests
    )

if __name__ == "__main__":
    main()
