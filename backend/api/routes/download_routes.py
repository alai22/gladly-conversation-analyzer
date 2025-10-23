"""
Download Management API Routes

This module provides API endpoints for managing Gladly conversation downloads
through the web interface.
"""

import os
import json
import threading
import time
from datetime import datetime
from flask import Blueprint, request, jsonify
from typing import Dict, Optional
import logging
from dotenv import load_dotenv

from backend.services.gladly_download_service import GladlyDownloadService
from backend.services.conversation_tracker import ConversationTracker
from backend.services.s3_conversation_aggregator import S3ConversationAggregator
from backend.utils.config import Config

# Load environment variables from .env file
load_dotenv()

# Configure logging
logger = logging.getLogger(__name__)

# Create blueprint
download_bp = Blueprint('download', __name__, url_prefix='/api/download')

# Global download state
download_state = {
    'is_running': False,
    'current_batch': 0,
    'total_batches': 0,
    'downloaded_count': 0,
    'failed_count': 0,
    'start_time': None,
    'end_time': None,
    'error': None,
    'progress_percentage': 0
}

# Global download service instance
download_service: Optional[GladlyDownloadService] = None
download_thread: Optional[threading.Thread] = None

@download_bp.route('/status', methods=['GET'])
def get_download_status():
    """Get current download status"""
    try:
        # Calculate progress percentage
        if download_state['total_batches'] > 0:
            download_state['progress_percentage'] = (download_state['current_batch'] / download_state['total_batches']) * 100
        
        # Calculate elapsed time
        elapsed_time = None
        if download_state['start_time']:
            elapsed_time = (datetime.now() - download_state['start_time']).total_seconds()
        
        return jsonify({
            'status': 'success',
            'data': {
                'is_running': download_state['is_running'],
                'current_batch': download_state['current_batch'],
                'total_batches': download_state['total_batches'],
                'downloaded_count': download_state['downloaded_count'],
                'failed_count': download_state['failed_count'],
                'progress_percentage': round(download_state['progress_percentage'], 2),
                'start_time': download_state['start_time'].isoformat() if download_state['start_time'] else None,
                'elapsed_time': elapsed_time,
                'error': download_state['error']
            }
        })
    except Exception as e:
        logger.error(f"Error getting download status: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

@download_bp.route('/start', methods=['POST'])
def start_download():
    """Start a new download batch"""
    global download_service, download_thread, download_state
    
    try:
        # Check if download is already running
        if download_state['is_running']:
            return jsonify({'status': 'error', 'message': 'Download is already running'}), 400
        
        # Get request data
        data = request.get_json() or {}
        batch_size = data.get('batch_size', 500)
        max_duration_minutes = data.get('max_duration_minutes', 30)
        start_date = data.get('start_date')
        end_date = data.get('end_date')
        
        # Validate batch size
        if not isinstance(batch_size, int) or batch_size <= 0:
            return jsonify({'status': 'error', 'message': 'Invalid batch size'}), 400
        
        # Validate date parameters
        if start_date and not isinstance(start_date, str):
            return jsonify({'status': 'error', 'message': 'Invalid start_date format'}), 400
        
        if end_date and not isinstance(end_date, str):
            return jsonify({'status': 'error', 'message': 'Invalid end_date format'}), 400
        
        # Validate date range
        if start_date and end_date and start_date > end_date:
            return jsonify({'status': 'error', 'message': 'Start date must be before end date'}), 400
        
        # Initialize download service
        download_service = GladlyDownloadService()
        
        # Reset download state
        download_state.update({
            'is_running': True,
            'current_batch': 0,
            'total_batches': batch_size,
            'downloaded_count': 0,
            'failed_count': 0,
            'start_time': datetime.now(),
            'end_time': None,
            'error': None,
            'progress_percentage': 0
        })
        
        # Start download in background thread
        download_thread = threading.Thread(
            target=_run_download,
            args=(batch_size, max_duration_minutes, start_date, end_date),
            daemon=True
        )
        download_thread.start()
        
        logger.info(f"Started download batch: {batch_size} conversations")
        
        return jsonify({
            'status': 'success',
            'message': f'Download started with batch size {batch_size}',
            'data': {
                'batch_size': batch_size,
                'max_duration_minutes': max_duration_minutes
            }
        })
        
    except Exception as e:
        logger.error(f"Error starting download: {e}")
        download_state['error'] = str(e)
        download_state['is_running'] = False
        return jsonify({'status': 'error', 'message': str(e)}), 500

@download_bp.route('/stop', methods=['POST'])
def stop_download():
    """Stop the current download"""
    global download_state
    
    try:
        if not download_state['is_running']:
            return jsonify({'status': 'error', 'message': 'No download is currently running'}), 400
        
        # Stop the download
        download_state['is_running'] = False
        download_state['end_time'] = datetime.now()
        
        logger.info("Download stopped by user")
        
        return jsonify({
            'status': 'success',
            'message': 'Download stopped successfully'
        })
        
    except Exception as e:
        logger.error(f"Error stopping download: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

@download_bp.route('/history', methods=['GET'])
def get_download_history():
    """Get detailed conversation download history"""
    try:
        # Get query parameters for pagination
        limit = request.args.get('limit', 100, type=int)
        offset = request.args.get('offset', 0, type=int)
        
        # Initialize conversation tracker
        tracker = ConversationTracker()
        
        # Get conversation history with pagination
        conversations = tracker.get_conversation_history(limit=limit, offset=offset)
        
        # Get conversation statistics
        stats = tracker.get_conversation_stats()
        
        return jsonify({
            'status': 'success',
            'data': {
                'conversations': conversations,
                'pagination': {
                    'limit': limit,
                    'offset': offset,
                    'total': stats['total_downloaded']
                },
                'stats': stats
            }
        })
        
    except Exception as e:
        logger.error(f"Error getting download history: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

@download_bp.route('/stats', methods=['GET'])
def get_download_stats():
    """Get overall download statistics"""
    try:
        # Initialize conversation tracker
        tracker = ConversationTracker()
        
        # Get conversation statistics
        stats = tracker.get_conversation_stats()
        
        # Get total conversations in CSV
        csv_file = "data/conversation_metrics.csv"
        total_in_csv = 0
        if os.path.exists(csv_file):
            try:
                import csv
                with open(csv_file, 'r', encoding='utf-8') as f:
                    reader = csv.DictReader(f)
                    total_in_csv = sum(1 for row in reader if row.get('Conversation ID', '').strip())
            except Exception:
                pass
        
        completion_percentage = (stats['total_downloaded'] / total_in_csv * 100) if total_in_csv > 0 else 0
        
        return jsonify({
            'status': 'success',
            'data': {
                'total_downloaded': stats['total_downloaded'],
                'total_in_csv': total_in_csv,
                'remaining': max(0, total_in_csv - stats['total_downloaded']),
                'completion_percentage': round(completion_percentage, 2),
                'date_range': stats['date_range'],
                'channels': stats['channels'],
                'agents': stats['agents'],
                'topics': stats['topics']
            }
        })
        
    except Exception as e:
        logger.error(f"Error getting download stats: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

def _run_download(batch_size: int, max_duration_minutes: int, start_date: str = None, end_date: str = None):
    """Run the download in background thread"""
    global download_state, download_service
    
    try:
        if not download_service:
            download_state['error'] = 'Download service not initialized'
            download_state['is_running'] = False
            return
        
        # Run the download
        download_service.download_batch(
            csv_file="data/conversation_metrics.csv",
            output_file="gladly_conversations_batch.jsonl",
            max_duration_minutes=max_duration_minutes,
            batch_size=batch_size,
            start_date=start_date,
            end_date=end_date,
            progress_callback=_update_progress
        )
        
        # Mark as completed
        download_state['is_running'] = False
        download_state['end_time'] = datetime.now()
        
        logger.info("Download completed successfully")
        
    except Exception as e:
        logger.error(f"Error in download thread: {e}")
        download_state['error'] = str(e)
        download_state['is_running'] = False
        download_state['end_time'] = datetime.now()

@download_bp.route('/aggregate', methods=['POST'])
def aggregate_conversations():
    """Aggregate downloaded conversations and refresh RAG data"""
    try:
        # Initialize aggregator
        aggregator = S3ConversationAggregator()
        
        # Perform aggregation
        result = aggregator.refresh_rag_data()
        
        if result['status'] == 'success':
            return jsonify({
                'status': 'success',
                'message': f"Successfully aggregated {result['total_conversations']} conversations from {result['files_processed']} files",
                'data': result
            })
        else:
            return jsonify({
                'status': 'warning',
                'message': result.get('message', 'Aggregation completed with warnings'),
                'data': result
            }), 200
            
    except Exception as e:
        logger.error(f"Error aggregating conversations: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

@download_bp.route('/aggregate/status', methods=['GET'])
def get_aggregation_status():
    """Get status of aggregated conversation file"""
    try:
        aggregator = S3ConversationAggregator()
        status = aggregator.get_aggregation_status()
        
        return jsonify({
            'status': 'success',
            'data': status
        })
        
    except Exception as e:
        logger.error(f"Error getting aggregation status: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 500
