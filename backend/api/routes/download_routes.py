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
        
        # Validate batch size
        if not isinstance(batch_size, int) or batch_size <= 0:
            return jsonify({'status': 'error', 'message': 'Invalid batch size'}), 400
        
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
            args=(batch_size, max_duration_minutes),
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
    """Get download history and statistics"""
    try:
        # Get list of downloaded files
        downloaded_files = []
        for file in os.listdir('.'):
            if file.startswith('gladly_conversations') and file.endswith('.jsonl'):
                file_path = file
                file_size = os.path.getsize(file_path)
                file_mtime = datetime.fromtimestamp(os.path.getmtime(file_path))
                
                # Count conversations in file
                conversation_count = 0
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        for line in f:
                            if line.strip():
                                conversation_count += 1
                except Exception:
                    pass
                
                downloaded_files.append({
                    'filename': file,
                    'size_mb': round(file_size / (1024 * 1024), 2),
                    'conversation_count': conversation_count,
                    'created_at': file_mtime.isoformat()
                })
        
        # Sort by creation time (newest first)
        downloaded_files.sort(key=lambda x: x['created_at'], reverse=True)
        
        return jsonify({
            'status': 'success',
            'data': {
                'files': downloaded_files,
                'total_files': len(downloaded_files)
            }
        })
        
    except Exception as e:
        logger.error(f"Error getting download history: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

@download_bp.route('/stats', methods=['GET'])
def get_download_stats():
    """Get overall download statistics"""
    try:
        # Analyze all downloaded files
        total_conversations = 0
        total_size_mb = 0
        
        for file in os.listdir('.'):
            if file.startswith('gladly_conversations') and file.endswith('.jsonl'):
                file_size = os.path.getsize(file)
                total_size_mb += file_size / (1024 * 1024)
                
                # Count conversations
                try:
                    with open(file, 'r', encoding='utf-8') as f:
                        for line in f:
                            if line.strip():
                                total_conversations += 1
                except Exception:
                    pass
        
        # Get total conversations in CSV
        csv_file = "Conversation Metrics (ID, Topic, Channel, Agent).csv"
        total_in_csv = 0
        if os.path.exists(csv_file):
            try:
                import csv
                with open(csv_file, 'r', encoding='utf-8') as f:
                    reader = csv.DictReader(f)
                    total_in_csv = sum(1 for row in reader if row.get('Conversation ID', '').strip())
            except Exception:
                pass
        
        completion_percentage = (total_conversations / total_in_csv * 100) if total_in_csv > 0 else 0
        
        return jsonify({
            'status': 'success',
            'data': {
                'total_downloaded': total_conversations,
                'total_in_csv': total_in_csv,
                'remaining': max(0, total_in_csv - total_conversations),
                'completion_percentage': round(completion_percentage, 2),
                'total_size_mb': round(total_size_mb, 2)
            }
        })
        
    except Exception as e:
        logger.error(f"Error getting download stats: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

def _run_download(batch_size: int, max_duration_minutes: int):
    """Run the download in background thread"""
    global download_state, download_service
    
    try:
        if not download_service:
            download_state['error'] = 'Download service not initialized'
            download_state['is_running'] = False
            return
        
        # Run the download
        download_service.download_batch(
            csv_file="Conversation Metrics (ID, Topic, Channel, Agent).csv",
            output_file="gladly_conversations_batch.jsonl",
            max_duration_minutes=max_duration_minutes,
            batch_size=batch_size,
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

def _update_progress(current: int, total: int, downloaded: int, failed: int):
    """Update download progress"""
    global download_state
    
    download_state.update({
        'current_batch': current,
        'total_batches': total,
        'downloaded_count': downloaded,
        'failed_count': failed
    })
