#!/usr/bin/env python3
"""
Batched Gladly Conversation Downloader

This script downloads conversation items in batches with time limits
to avoid long-running processes.
"""

import csv
import json
import os
import time
import requests
from typing import List, Dict, Optional
from datetime import datetime, timedelta
import logging
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('gladly_batch_download.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class BatchedGladlyDownloader:
    """Downloads conversation items in batches with time limits"""
    
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
    
    def get_processed_ids(self, output_file: str) -> set:
        """Get already processed conversation IDs from output file"""
        processed_ids = set()
        
        if not os.path.exists(output_file):
            return processed_ids
        
        try:
            with open(output_file, 'r', encoding='utf-8') as f:
                for line in f:
                    if line.strip():
                        try:
                            data = json.loads(line)
                            if '_metadata' in data and 'conversation_id' in data['_metadata']:
                                processed_ids.add(data['_metadata']['conversation_id'])
                        except json.JSONDecodeError:
                            continue
        except Exception as e:
            logger.warning(f"Could not read existing output file: {e}")
        
        logger.info(f"Found {len(processed_ids)} already processed conversations")
        return processed_ids
    
    def download_batch(self, csv_file: str, output_file: str = None, 
                      max_duration_minutes: int = 5, batch_size: int = 50):
        """Download conversations in batches with time limit"""
        
        conversation_ids = self.read_conversation_ids_from_csv(csv_file)
        
        if not conversation_ids:
            logger.error("No conversation IDs found in CSV file")
            return
        
        if output_file is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_file = f"gladly_conversations_batch_{timestamp}.jsonl"
        
        # Get already processed IDs
        processed_ids = self.get_processed_ids(output_file)
        
        # Filter out already processed IDs
        remaining_ids = [cid for cid in conversation_ids if cid not in processed_ids]
        
        if not remaining_ids:
            logger.info("All conversations have already been processed!")
            return
        
        logger.info(f"Starting batch download of {len(remaining_ids)} remaining conversations")
        logger.info(f"Time limit: {max_duration_minutes} minutes")
        logger.info(f"Output file: {output_file}")
        
        start_time = datetime.now()
        end_time = start_time + timedelta(minutes=max_duration_minutes)
        
        downloaded_count = 0
        failed_count = 0
        
        with open(output_file, 'a', encoding='utf-8') as outfile:
            for i, conversation_id in enumerate(remaining_ids, 1):
                # Check if we've exceeded the time limit
                if datetime.now() >= end_time:
                    logger.info(f"Time limit reached ({max_duration_minutes} minutes). Stopping download.")
                    break
                
                logger.info(f"Processing conversation {i}/{len(remaining_ids)}: {conversation_id}")
                
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
                
                # Add small delay to avoid rate limiting
                time.sleep(0.1)
                
                # Log progress every batch_size
                if i % batch_size == 0:
                    elapsed = datetime.now() - start_time
                    logger.info(f"Progress: {i}/{len(remaining_ids)} conversations processed in {elapsed}")
        
        elapsed_time = datetime.now() - start_time
        logger.info(f"Batch download completed!")
        logger.info(f"Time elapsed: {elapsed_time}")
        logger.info(f"Successfully downloaded: {downloaded_count}")
        logger.info(f"Failed downloads: {failed_count}")
        logger.info(f"Output saved to: {output_file}")
        
        # Show remaining count
        remaining_after_batch = len(remaining_ids) - downloaded_count - failed_count
        logger.info(f"Remaining conversations to process: {remaining_after_batch}")

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
    downloader = BatchedGladlyDownloader(api_key, agent_email)
    
    # Download batch with 5-minute limit
    downloader.download_batch(
        csv_file=csv_file,
        output_file="gladly_conversations_batch.jsonl",
        max_duration_minutes=5,
        batch_size=25
    )

if __name__ == "__main__":
    main()
