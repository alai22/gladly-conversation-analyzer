"""
Gladly Download Service

This service handles downloading conversation data from Gladly API
and integrates with the existing Flask application architecture.
"""

import os
import csv
import json
import time
import requests
from typing import List, Dict, Optional, Callable
from datetime import datetime, timedelta
import logging
from dotenv import load_dotenv

from backend.utils.config import Config
from backend.services.storage_service import StorageService
from backend.services.conversation_tracker import ConversationTracker

# Load environment variables
load_dotenv()

logger = logging.getLogger(__name__)

class GladlyDownloadService:
    """Service for downloading Gladly conversation data"""
    
    def __init__(self):
        self.api_key = os.getenv('GLADLY_API_KEY')
        self.agent_email = os.getenv('GLADLY_AGENT_EMAIL')
        self.base_url = "https://halocollar.us-1.gladly.com"
        
        if not self.api_key or not self.agent_email:
            raise ValueError("GLADLY_API_KEY and GLADLY_AGENT_EMAIL must be set")
        
        # Initialize session with Basic Auth
        self.session = requests.Session()
        self.session.auth = (self.agent_email, self.api_key)
        self.session.headers.update({
            'Content-Type': 'application/json',
            'Accept': 'application/json',
            'User-Agent': 'Gladly-Conversation-Analyzer/1.0'
        })
        
        # Initialize storage service
        self.storage_service = StorageService()
        
        # Initialize conversation tracker
        self.conversation_tracker = ConversationTracker()
        
    def download_conversation_items(self, conversation_id: str) -> Optional[Dict]:
        """Download conversation items for a specific conversation ID"""
        url = f"{self.base_url}/api/v1/conversations/{conversation_id}/items"
        
        try:
            logger.info(f"[API CALL] Starting download for conversation ID: {conversation_id}")
            print(f"[GLADLY API] GET {url} - Starting request for conversation {conversation_id}")
            
            start_time = time.time()
            response = self.session.get(url, timeout=30)
            elapsed = time.time() - start_time
            
            logger.info(f"[API CALL] Response for {conversation_id}: HTTP {response.status_code} (took {elapsed:.2f}s)")
            print(f"[GLADLY API] Response: HTTP {response.status_code} for conversation {conversation_id} (took {elapsed:.2f}s)")
            
            if response.status_code == 200:
                if not response.text.strip():
                    logger.warning(f"Empty response for conversation {conversation_id}")
                    return None
                
                try:
                    data = response.json()
                    # The API returns a list of items directly
                    if isinstance(data, list):
                        logger.debug(f"Successfully downloaded {len(data)} items for conversation {conversation_id}")
                        return {'items': data}  # Wrap in object for consistency
                    else:
                        logger.debug(f"Successfully downloaded {len(data.get('items', []))} items for conversation {conversation_id}")
                        return data
                except json.JSONDecodeError as e:
                    logger.error(f"JSON decode error for conversation {conversation_id}: {e}")
                    return None
            elif response.status_code == 404:
                logger.warning(f"Conversation {conversation_id} not found (404)")
                return None
            elif response.status_code == 401:
                logger.error(f"Unauthorized access for conversation {conversation_id} (401)")
                return None
            else:
                logger.error(f"Failed to download conversation {conversation_id}: HTTP {response.status_code}")
                return None
                
        except requests.exceptions.RequestException as e:
            logger.error(f"Request error for conversation {conversation_id}: {e}")
            return None
    
    def read_conversation_ids_from_csv(self, csv_file: str) -> List[str]:
        """Read conversation IDs from the CSV file"""
        logger.info(f"Reading conversation IDs from CSV file: {csv_file}")
        
        # Check if file exists and add debugging info
        if not os.path.exists(csv_file):
            logger.error(f"CSV file not found: {csv_file}")
            logger.error(f"Current working directory: {os.getcwd()}")
            logger.error(f"Files in current directory: {os.listdir('.')}")
            if os.path.exists('data'):
                logger.error(f"Files in data directory: {os.listdir('data')}")
            return []
        
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
                      max_duration_minutes: int = 30, batch_size: int = 500,
                      start_date: str = None, end_date: str = None,
                      progress_callback: Optional[Callable] = None):
        """Download conversations in batches with time limit"""
        
        conversation_ids = self.read_conversation_ids_from_csv(csv_file)
        
        if not conversation_ids:
            logger.error("No conversation IDs found in CSV file")
            return
        
        # Filter by date range if specified
        if start_date or end_date:
            conversation_ids = self.filter_conversations_by_date(
                csv_file, conversation_ids, start_date, end_date
            )
            logger.info(f"After date filtering: {len(conversation_ids)} conversations")
        
        if not conversation_ids:
            logger.info("No conversations found in the specified date range")
            return
        
        if output_file is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_file = f"gladly_conversations_batch_{timestamp}.jsonl"
        
        # Get already processed IDs from conversation tracker
        processed_ids = self.conversation_tracker.get_downloaded_conversation_ids()
        
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
                
                # Update progress to show we're starting this conversation (even before API call completes)
                # This helps show progress immediately instead of waiting for first API call to complete
                if progress_callback and i == 1:
                    # For the first conversation, update immediately to show we've started
                    progress_callback(0, len(remaining_ids), downloaded_count, failed_count)
                
                logger.info(f"[PROGRESS] Processing conversation {i}/{len(remaining_ids)}: {conversation_id}")
                print(f"[PROGRESS] Starting conversation {i}/{len(remaining_ids)}: {conversation_id}")
                
                # Get conversation metadata from CSV
                conversation_metadata = self.get_conversation_metadata_from_csv(csv_file, conversation_id)
                
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
                    
                    # Track the conversation
                    if conversation_metadata:
                        self.conversation_tracker.track_conversation(
                            conversation_id=conversation_id,
                            conversation_date=conversation_metadata.get('conversation_date', ''),
                            download_timestamp=datetime.now().isoformat(),
                            file_name=output_file,
                            topics=conversation_metadata.get('topics', ''),
                            channel=conversation_metadata.get('channel', ''),
                            agent=conversation_metadata.get('agent', '')
                        )
                else:
                    failed_count += 1
                
                # Update progress callback
                if progress_callback:
                    progress_callback(i, len(remaining_ids), downloaded_count, failed_count)
                
                # Add small delay to avoid rate limiting
                time.sleep(0.1)
                
                # Log progress every 50 conversations
                if i % 50 == 0:
                    elapsed = datetime.now() - start_time
                    logger.info(f"Progress: {i}/{len(remaining_ids)} conversations processed in {elapsed}")
        
        elapsed_time = datetime.now() - start_time
        logger.info(f"Batch download completed!")
        logger.info(f"Time elapsed: {elapsed_time}")
        logger.info(f"Successfully downloaded: {downloaded_count}")
        logger.info(f"Failed downloads: {failed_count}")
        logger.info(f"Output saved to: {output_file}")
        
        # Upload to S3 if configured
        if Config.STORAGE_TYPE == 's3' and Config.S3_BUCKET_NAME:
            try:
                self._upload_to_s3(output_file)
            except Exception as e:
                logger.error(f"Failed to upload to S3: {e}")
        
        # Show remaining count
        remaining_after_batch = len(remaining_ids) - downloaded_count - failed_count
        logger.info(f"Remaining conversations to process: {remaining_after_batch}")
    
    def _upload_to_s3(self, local_file: str):
        """Upload downloaded file to S3"""
        try:
            # Generate S3 key with timestamp
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            s3_key = f"gladly-conversations/{timestamp}_{os.path.basename(local_file)}"
            
            logger.info(f"Uploading {local_file} to S3: s3://{Config.S3_BUCKET_NAME}/{s3_key}")
            
            # Use boto3 to upload the file
            import boto3
            s3_client = boto3.client('s3')
            
            with open(local_file, 'rb') as f:
                s3_client.put_object(
                    Bucket=Config.S3_BUCKET_NAME,
                    Key=s3_key,
                    Body=f,
                    ContentType='application/json'
                )
            
            logger.info(f"Successfully uploaded to S3: {s3_key}")
                
        except Exception as e:
            logger.error(f"Error uploading to S3: {e}")
            raise
    
    def get_download_statistics(self) -> Dict:
        """Get download statistics"""
        stats = {
            'total_downloaded': 0,
            'total_size_mb': 0,
            'files': []
        }
        
        try:
            for file in os.listdir('.'):
                if file.startswith('gladly_conversations') and file.endswith('.jsonl'):
                    file_size = os.path.getsize(file)
                    file_mtime = datetime.fromtimestamp(os.path.getmtime(file))
                    
                    # Count conversations in file
                    conversation_count = 0
                    try:
                        with open(file, 'r', encoding='utf-8') as f:
                            for line in f:
                                if line.strip():
                                    conversation_count += 1
                    except Exception:
                        pass
                    
                    stats['files'].append({
                        'filename': file,
                        'size_mb': round(file_size / (1024 * 1024), 2),
                        'conversation_count': conversation_count,
                        'created_at': file_mtime.isoformat()
                    })
                    
                    stats['total_downloaded'] += conversation_count
                    stats['total_size_mb'] += file_size / (1024 * 1024)
            
            stats['total_size_mb'] = round(stats['total_size_mb'], 2)
            
        except Exception as e:
            logger.error(f"Error getting download statistics: {e}")
        
        return stats
    
    def filter_conversations_by_date(self, csv_file: str, conversation_ids: List[str], 
                                   start_date: str = None, end_date: str = None) -> List[str]:
        """Filter conversation IDs by date range from CSV file"""
        
        try:
            filtered_ids = []
            
            with open(csv_file, 'r', encoding='utf-8') as file:
                reader = csv.DictReader(file)
                
                for row in reader:
                    conversation_id = row.get('Conversation ID', '').strip()
                    
                    # Skip if this conversation ID is not in our list
                    if conversation_id not in conversation_ids:
                        continue
                    
                    # Get the timestamp from the CSV
                    timestamp_str = row.get('Timestamp Created At Date', '').strip()
                    
                    if not timestamp_str:
                        continue
                    
                    try:
                        # Parse the timestamp (format: YYYY-MM-DD)
                        conversation_date = datetime.strptime(timestamp_str, '%Y-%m-%d').date()
                        
                        # Check date range
                        include_conversation = True
                        
                        if start_date:
                            start_date_obj = datetime.strptime(start_date, '%Y-%m-%d').date()
                            if conversation_date < start_date_obj:
                                include_conversation = False
                        
                        if end_date:
                            end_date_obj = datetime.strptime(end_date, '%Y-%m-%d').date()
                            if conversation_date > end_date_obj:
                                include_conversation = False
                        
                        if include_conversation:
                            filtered_ids.append(conversation_id)
                            
                    except ValueError as e:
                        logger.warning(f"Could not parse date '{timestamp_str}' for conversation {conversation_id}: {e}")
                        continue
            
            logger.info(f"Date filtering: {len(filtered_ids)} conversations match date range")
            if start_date:
                logger.info(f"Start date filter: {start_date}")
            if end_date:
                logger.info(f"End date filter: {end_date}")
                
            return filtered_ids
            
        except Exception as e:
            logger.error(f"Error filtering conversations by date: {e}")
            # Return original list if filtering fails
            return conversation_ids
    
    def get_conversation_metadata_from_csv(self, csv_file: str, conversation_id: str) -> Optional[Dict]:
        """Get metadata for a specific conversation from CSV file"""
        try:
            with open(csv_file, 'r', encoding='utf-8') as file:
                reader = csv.DictReader(file)
                
                for row in reader:
                    if row.get('Conversation ID', '').strip() == conversation_id:
                        return {
                            'conversation_date': row.get('Timestamp Created At Date', '').strip(),
                            'topics': row.get('Topics', '').strip(),
                            'channel': row.get('Last Channel', '').strip(),
                            'agent': row.get('Assigned Agent Name - Current', '').strip(),
                            'conversation_link': row.get('Conversation Link', '').strip()
                        }
            
            logger.warning(f"No metadata found for conversation {conversation_id}")
            return None
            
        except Exception as e:
            logger.error(f"Error getting conversation metadata: {e}")
            return None
