"""
S3 Conversation Aggregation Service

This service aggregates conversation files from S3 into a single file
that the RAG system can use for analysis.
"""

import json
import boto3
import os
from datetime import datetime
from typing import List, Dict, Any, Optional, Tuple
import logging
from dotenv import load_dotenv

from backend.utils.config import Config

# Load environment variables
load_dotenv()

logger = logging.getLogger(__name__)

class S3ConversationAggregator:
    """Aggregates conversation files from S3 into a single file for RAG system"""
    
    def __init__(self):
        self.s3_client = boto3.client('s3')
        self.bucket_name = Config.S3_BUCKET_NAME
        self.region = Config.S3_REGION
        
        if not self.bucket_name:
            raise ValueError("S3_BUCKET_NAME not configured")
    
    def aggregate_conversations(self, target_key: str = None) -> Dict[str, Any]:
        """
        Aggregate all conversation files from S3 into a single file
        
        Args:
            target_key: S3 key for the aggregated file (defaults to Config.S3_FILE_KEY)
        
        Returns:
            Dict with aggregation statistics
        """
        if target_key is None:
            target_key = Config.S3_FILE_KEY
        
        logger.info(f"Starting conversation aggregation to s3://{self.bucket_name}/{target_key}")
        
        # Get all conversation files from S3 with diagnostics
        conversation_files, diagnostics = self._list_conversation_files(include_diagnostics=True)
        
        if not conversation_files:
            logger.warning("No conversation files found in S3")
            
            # Build detailed error message
            error_parts = ['No conversation files found matching the required pattern.']
            
            if diagnostics.get('error'):
                error_parts.append(f"\nError: {diagnostics['error']}")
            
            if not diagnostics.get('s3_accessible'):
                error_parts.append("\n⚠️ Cannot access S3 bucket - check IAM permissions.")
            
            if diagnostics.get('total_files_in_prefix', 0) == 0:
                error_parts.append(f"\n📁 No files found in S3 prefix: '{diagnostics['prefix_searched']}'")
                error_parts.append("\n💡 Possible reasons:")
                error_parts.append("   • No conversations have been downloaded yet")
                error_parts.append("   • Downloads are still in progress (files upload after download completes)")
                error_parts.append("   • Files are stored in a different S3 prefix")
            else:
                error_parts.append(f"\n📁 Found {diagnostics['total_files_in_prefix']} files in prefix, but none match the pattern:")
                error_parts.append(f"   Required: {diagnostics['pattern_required']}")
                
                if diagnostics.get('files_ending_jsonl', 0) > 0:
                    error_parts.append(f"\n   Found {diagnostics['files_ending_jsonl']} .jsonl files, but they don't contain 'gladly_conversations' in the filename:")
                    for non_match in diagnostics.get('non_matching_files', [])[:5]:
                        if non_match.get('reason') == 'Missing "gladly_conversations" in filename':
                            error_parts.append(f"     • {non_match['key']}")
                    if len(diagnostics.get('non_matching_files', [])) > 5:
                        error_parts.append(f"     ... and {len(diagnostics.get('non_matching_files', [])) - 5} more")
                else:
                    error_parts.append("\n   None of the files end with .jsonl")
                    if diagnostics.get('non_matching_files'):
                        error_parts.append("   Sample files found:")
                        for non_match in diagnostics.get('non_matching_files', [])[:3]:
                            error_parts.append(f"     • {non_match['key']}")
            
            return {
                'status': 'warning',
                'message': '\n'.join(error_parts),
                'files_processed': 0,
                'total_conversations': 0,
                'diagnostics': diagnostics
            }
        
        # Aggregate conversations
        all_conversations = []
        files_processed = 0
        
        for file_key in conversation_files:
            try:
                conversations = self._load_conversation_file(file_key)
                all_conversations.extend(conversations)
                files_processed += 1
                logger.info(f"Loaded {len(conversations)} conversations from {file_key}")
            except Exception as e:
                logger.error(f"Failed to load {file_key}: {e}")
        
        # Remove duplicates based on item ID and timestamp
        unique_items = self._deduplicate_conversations(all_conversations)
        
        # Upload aggregated file to S3
        self._upload_aggregated_file(unique_items, target_key)
        
        stats = {
            'status': 'success',
            'files_processed': files_processed,
            'total_conversations': len(unique_items),  # Keep name for API compatibility, but it's actually items
            'total_items': len(unique_items),  # Add explicit items count
            'duplicates_removed': len(all_conversations) - len(unique_items),
            'target_key': target_key,
            'aggregated_at': datetime.now().isoformat()
        }
        
        logger.info(f"Aggregation completed: {stats}")
        return stats
    
    def _list_conversation_files(self, include_diagnostics: bool = False) -> Tuple[List[str], Dict[str, Any]]:
        """
        List all conversation files in S3
        
        Args:
            include_diagnostics: If True, return detailed diagnostics
            
        Returns:
            Tuple of (matching_files, diagnostics_dict)
        """
        diagnostics = {
            's3_accessible': False,
            'prefix_searched': 'gladly-conversations/',
            'pattern_required': 'files ending with .jsonl and containing "gladly_conversations"',
            'total_files_in_prefix': 0,
            'files_ending_jsonl': 0,
            'matching_files': [],
            'non_matching_files': [],
            'error': None,
            'bucket_name': self.bucket_name
        }
        
        try:
            # Test S3 access
            try:
                self.s3_client.head_bucket(Bucket=self.bucket_name)
                diagnostics['s3_accessible'] = True
            except Exception as access_error:
                diagnostics['error'] = f"S3 access error: {str(access_error)}"
                logger.error(f"Failed to access S3 bucket {self.bucket_name}: {access_error}")
                return ([], diagnostics)
            
            # List objects with prefix (handle pagination)
            matching_files = []
            all_files = []
            file_mod_times = {}  # Store mod times for sorting
            
            paginator = self.s3_client.get_paginator('list_objects_v2')
            pages = paginator.paginate(
                Bucket=self.bucket_name,
                Prefix='gladly-conversations/'
            )
            
            # Process all pages
            for page in pages:
                if 'Contents' not in page:
                    continue
                    
                for obj in page['Contents']:
                    key = obj['Key']
                    last_modified = obj.get('LastModified')
                    
                    # Store modification time for sorting
                    if last_modified:
                        file_mod_times[key] = last_modified
                        if hasattr(last_modified, 'isoformat'):
                            last_modified_str = last_modified.isoformat()
                        else:
                            last_modified_str = str(last_modified)
                    else:
                        last_modified_str = 'Unknown'
                    
                    diagnostics['total_files_in_prefix'] += 1
                    
                    all_files.append({
                        'key': key,
                        'size': obj.get('Size', 0),
                        'last_modified': last_modified_str
                    })
                    
                    # Check if it ends with .jsonl
                    if key.endswith('.jsonl'):
                        diagnostics['files_ending_jsonl'] += 1
                        # Check if it contains gladly_conversations
                        if 'gladly_conversations' in key:
                            matching_files.append(key)
                            diagnostics['matching_files'].append({
                                'key': key,
                                'size': obj.get('Size', 0),
                                'last_modified': last_modified_str
                            })
                        else:
                            diagnostics['non_matching_files'].append({
                                'key': key,
                                'reason': 'Missing "gladly_conversations" in filename',
                                'size': obj.get('Size', 0)
                            })
                    else:
                        diagnostics['non_matching_files'].append({
                            'key': key,
                            'reason': 'Not a .jsonl file',
                            'size': obj.get('Size', 0)
                        })
            
            # Sort by modification time (newest first)
            if matching_files and file_mod_times:
                try:
                    # Use stored file_mod_times dict for sorting
                    matching_files.sort(
                        key=lambda x: file_mod_times.get(x, datetime(1970, 1, 1)), 
                        reverse=True
                    )
                    logger.info(f"Sorted {len(matching_files)} files by modification time")
                except Exception as e:
                    logger.error(f"Failed to sort files by modification time: {e}", exc_info=True)
                    # Continue without sorting rather than failing completely
            
            logger.info(f"Found {len(matching_files)} matching conversation files in S3 (out of {diagnostics['total_files_in_prefix']} total files)")
            
            return (matching_files, diagnostics)
            
        except self.s3_client.exceptions.NoSuchBucket:
            diagnostics['error'] = f"S3 bucket '{self.bucket_name}' does not exist"
            logger.error(f"S3 bucket {self.bucket_name} does not exist")
            return ([], diagnostics)
        except self.s3_client.exceptions.ClientError as e:
            error_code = e.response.get('Error', {}).get('Code', 'Unknown')
            diagnostics['error'] = f"S3 client error ({error_code}): {str(e)}"
            logger.error(f"Failed to list S3 files: {e}")
            return ([], diagnostics)
        except Exception as e:
            diagnostics['error'] = f"Unexpected error: {str(e)}"
            logger.error(f"Failed to list S3 files: {e}")
            return ([], diagnostics)
    
    def _load_conversation_file(self, file_key: str) -> List[Dict[str, Any]]:
        """Load conversations from a specific S3 file and flatten items"""
        try:
            response = self.s3_client.get_object(
                Bucket=self.bucket_name,
                Key=file_key
            )
            
            content = response['Body'].read().decode('utf-8')
            all_items = []
            
            for line in content.split('\n'):
                if line.strip():
                    try:
                        conversation_data = json.loads(line.strip())
                        
                        # Extract metadata if present
                        metadata = conversation_data.get('_metadata', {})
                        conversation_id_from_meta = metadata.get('conversation_id', '')
                        
                        # Check if this is a nested structure with 'items' array
                        if 'items' in conversation_data and isinstance(conversation_data['items'], list):
                            # Flatten: extract each item and add metadata
                            for item in conversation_data['items']:
                                # Ensure item has required fields from metadata
                                if conversation_id_from_meta and not item.get('conversationId'):
                                    item['conversationId'] = conversation_id_from_meta
                                # Store the flattened item
                                all_items.append(item)
                        else:
                            # Already flattened format - check if it has required fields
                            if not conversation_data.get('conversationId') and conversation_id_from_meta:
                                conversation_data['conversationId'] = conversation_id_from_meta
                            all_items.append(conversation_data)
                            
                    except json.JSONDecodeError:
                        logger.warning(f"Failed to parse line in {file_key}: {line[:100]}...")
            
            logger.debug(f"Loaded {len(all_items)} items from {file_key} (flattened from nested structure)")
            return all_items
            
        except Exception as e:
            logger.error(f"Failed to load {file_key}: {e}")
            return []
    
    def _deduplicate_conversations(self, conversations: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Remove duplicate conversation items based on item ID"""
        seen = set()
        unique_items = []
        
        for item in conversations:
            # Create a unique key based on item ID (not conversation ID, since multiple items can be in same conversation)
            item_id = item.get('id', '')
            # Also use timestamp if available for better deduplication
            timestamp = item.get('timestamp', '')
            unique_key = f"{item_id}_{timestamp}"
            
            if unique_key and unique_key not in seen:
                seen.add(unique_key)
                unique_items.append(item)
        
        logger.info(f"Deduplication: {len(conversations)} -> {len(unique_items)} items")
        return unique_items
    
    def _upload_aggregated_file(self, conversations: List[Dict[str, Any]], target_key: str):
        """Upload aggregated conversations to S3"""
        try:
            # Convert to JSONL format
            jsonl_content = '\n'.join(json.dumps(conv) for conv in conversations)
            
            # Upload to S3
            self.s3_client.put_object(
                Bucket=self.bucket_name,
                Key=target_key,
                Body=jsonl_content.encode('utf-8'),
                ContentType='application/json'
            )
            
            logger.info(f"Uploaded {len(conversations)} conversation items to s3://{self.bucket_name}/{target_key}")
            
        except Exception as e:
            logger.error(f"Failed to upload aggregated file: {e}")
            raise
    
    def get_aggregation_status(self) -> Dict[str, Any]:
        """Get status of current aggregated file"""
        try:
            response = self.s3_client.head_object(
                Bucket=self.bucket_name,
                Key=Config.S3_FILE_KEY
            )
            
            return {
                'exists': True,
                'last_modified': response['LastModified'].isoformat(),
                'size_bytes': response['ContentLength'],
                'size_mb': round(response['ContentLength'] / (1024 * 1024), 2)
            }
            
        except self.s3_client.exceptions.NoSuchKey:
            return {'exists': False}
        except Exception as e:
            logger.error(f"Failed to get aggregation status: {e}")
            return {'exists': False, 'error': str(e)}
    
    def refresh_rag_data(self) -> Dict[str, Any]:
        """Refresh RAG data by re-aggregating conversations"""
        logger.info("Refreshing RAG data with latest conversations")
        
        # Aggregate conversations
        result = self.aggregate_conversations()
        
        if result['status'] == 'success':
            logger.info(f"RAG data refreshed: {result['total_conversations']} conversations from {result['files_processed']} files")
            
            # Trigger RAG system refresh
            try:
                self._trigger_rag_refresh()
            except Exception as e:
                logger.warning(f"Failed to trigger RAG refresh: {e}")
        else:
            logger.warning(f"RAG data refresh failed: {result.get('message', 'Unknown error')}")
        
        return result
    
    def _trigger_rag_refresh(self):
        """Trigger RAG system to refresh conversation data"""
        try:
            import requests
            
            # Try to determine the base URL from environment or config
            base_url = os.getenv('FLASK_BASE_URL', 'http://localhost:5000')
            
            refresh_url = f"{base_url}/api/conversations/refresh"
            logger.info(f"Triggering RAG refresh at {refresh_url}")
            
            response = requests.post(refresh_url, timeout=30)
            if response.status_code == 200:
                result = response.json()
                logger.info(f"RAG system refresh triggered successfully: {result.get('message', '')}")
            else:
                logger.warning(f"RAG refresh failed with status {response.status_code}: {response.text}")
        except requests.exceptions.ConnectionError as e:
            logger.warning(f"Could not connect to Flask app for RAG refresh (this is normal if app isn't running yet): {e}")
            logger.info("Conversation service will refresh on next query or manual refresh")
        except Exception as e:
            logger.warning(f"Failed to trigger RAG refresh via HTTP: {e}")
            logger.info("Conversation service will refresh on next query or manual refresh")
            # Don't raise - this is non-critical
