"""
API routes for conversation data interactions
"""

import threading
from datetime import datetime
from typing import Dict, Optional
from flask import Blueprint, request, jsonify, g
from ...models.response import SearchResult
from ...utils.logging import get_logger

logger = get_logger('conversation_routes')

# Create blueprint
conversation_bp = Blueprint('conversations', __name__, url_prefix='/api/conversations')

# Global topic extraction state (for async processing)
topic_extraction_state = {
    'is_running': False,
    'current': 0,
    'total': 0,
    'processed_count': 0,
    'skipped_count': 0,
    'failed_count': 0,
    'start_time': None,
    'end_time': None,
    'error': None,
    'progress_percentage': 0,
    'start_date': None,
    'end_date': None,
    'dates_processed': []
}

# Global topic extraction thread
topic_extraction_thread: Optional[threading.Thread] = None


@conversation_bp.route('/summary')
def conversations_summary():
    """Get conversation data summary"""
    try:
        # Get service from container (injected via Flask's g)
        # Use getattr with default None to avoid AttributeError
        service_container = getattr(g, 'service_container', None)
        if not service_container:
            logger.error("Service container not available in request context")
            return jsonify({'error': 'Service container not initialized'}), 500
        
        conversation_service = service_container.get_conversation_service()
        summary = conversation_service.get_summary()
        
        return jsonify({
            'success': True,
            'summary': summary.to_string()
        })
    
    except Exception as e:
        logger.error(f"Conversation summary error: {str(e)}")
        return jsonify({'error': str(e)}), 500


@conversation_bp.route('/search', methods=['POST'])
def conversations_search():
    """Search conversations"""
    try:
        # Get service from container (injected via Flask's g)
        # Use getattr with default None to avoid AttributeError
        service_container = getattr(g, 'service_container', None)
        if not service_container:
            logger.error("Service container not available in request context")
            return jsonify({'error': 'Service container not initialized'}), 500
        
        conversation_service = service_container.get_conversation_service()
        
        data = request.get_json()
        query = data.get('query')
        limit = data.get('limit', 10)
        
        if not query:
            return jsonify({'error': 'Query is required'}), 400
        
        logger.info(f"Conversation search request: query={query}, limit={limit}")
        
        results = conversation_service.semantic_search_conversations(query, limit)
        
        search_result = SearchResult(
            items=results,
            count=len(results),
            query=query,
            search_type='semantic'
        )
        
        return jsonify({
            'success': True,
            'results': results,
            'count': len(results)
        })
    
    except Exception as e:
        logger.error(f"Conversation search error: {str(e)}")
        return jsonify({'error': str(e)}), 500


@conversation_bp.route('/<conversation_id>', methods=['GET'])
def get_conversation(conversation_id):
    """Get all items for a specific conversation ID"""
    try:
        # Get service from container (injected via Flask's g)
        # Use getattr with default None to avoid AttributeError
        service_container = getattr(g, 'service_container', None)
        if not service_container:
            logger.error("Service container not available in request context")
            return jsonify({'error': 'Service container not initialized'}), 500
        
        conversation_service = service_container.get_conversation_service()
        
        logger.info(f"Get conversation request: conversation_id={conversation_id}")
        
        items = conversation_service.get_conversation_by_id(conversation_id)
        
        if not items:
            return jsonify({
                'success': False,
                'error': f'Conversation {conversation_id} not found',
                'items': []
            }), 404
        
        return jsonify({
            'success': True,
            'conversation_id': conversation_id,
            'items': items,
            'count': len(items)
        })
    
    except Exception as e:
        logger.error(f"Get conversation error: {str(e)}")
        return jsonify({'error': str(e)}), 500


@conversation_bp.route('/topic-trends', methods=['GET'])
def get_topic_trends():
    """Get conversation topic trends for a specific date (uses pre-extracted topics)"""
    try:
        # Get service from container (injected via Flask's g)
        service_container = getattr(g, 'service_container', None)
        if not service_container:
            logger.error("Service container not available in request context")
            return jsonify({'error': 'Service container not initialized'}), 500
        
        # Get date parameter (default to 2025-10-20 for prototype)
        date = request.args.get('date', '2025-10-20')
        
        logger.info(f"Topic trends request: date={date}")
        
        # Import topic storage service
        from ...services.topic_storage_service import TopicStorageService
        
        topic_storage = TopicStorageService()
        
        # Get pre-extracted topics for the date
        topic_mapping = topic_storage.get_topics_for_date(date)
        
        if not topic_mapping:
            return jsonify({
                'success': False,
                'date': date,
                'topics': [],
                'data': [],
                'total': 0,
                'message': f'No topics extracted for date {date}. Please extract topics first in Settings.'
            })
        
        # Aggregate topics
        topic_counts = {}
        for conversation_id, topic in topic_mapping.items():
            topic_counts[topic] = topic_counts.get(topic, 0) + 1
        
        total_conversations = len(topic_mapping)
        
        # Calculate percentages and format data
        topics = sorted(topic_counts.keys())
        data = []
        for topic in topics:
            count = topic_counts[topic]
            percentage = (count / total_conversations * 100) if total_conversations > 0 else 0
            data.append({
                'topic': topic,
                'count': count,
                'percentage': round(percentage, 2)
            })
        
        # Sort by count (descending)
        data.sort(key=lambda x: x['count'], reverse=True)
        
        logger.info(f"Topic trends calculated: {len(topics)} unique topics, {total_conversations} total conversations")
        
        return jsonify({
            'success': True,
            'date': date,
            'topics': topics,
            'data': data,
            'total': total_conversations
        })
    
    except Exception as e:
        logger.error(f"Topic trends error: {str(e)}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        return jsonify({'error': str(e)}), 500


@conversation_bp.route('/extract-topics', methods=['POST'])
def extract_topics():
    """Start topic extraction in background thread (async)"""
    global topic_extraction_state, topic_extraction_thread
    
    try:
        # Check if extraction is already running
        if topic_extraction_state['is_running']:
            return jsonify({
                'success': False,
                'error': 'Extraction already running',
                'message': 'Topic extraction is already in progress. Please wait for it to complete.'
            }), 400
        
        # Get service from container (injected via Flask's g)
        service_container = getattr(g, 'service_container', None)
        if not service_container:
            logger.error("Service container not available in request context")
            return jsonify({'error': 'Service container not initialized'}), 500
        
        conversation_service = service_container.get_conversation_service()
        claude_service = service_container.get_claude_service()
        
        # Check if Claude service is initialized
        if claude_service is None:
            error_msg = "Claude API service is not initialized. Please check ANTHROPIC_API_KEY configuration."
            logger.error(error_msg)
            return jsonify({
                'error': error_msg,
                'details': 'ANTHROPIC_API_KEY environment variable is not set or invalid. Please configure it in your .env file or environment.'
            }), 503
        
        # Get date parameters from request body
        data = request.get_json() or {}
        date = data.get('date')  # Single date (for backward compatibility)
        start_date = data.get('start_date', date)
        end_date = data.get('end_date', date)
        
        # Validate date parameters
        if not start_date or not end_date:
            return jsonify({
                'success': False,
                'error': 'Missing date parameters',
                'details': 'Please provide either "date" (single date) or both "start_date" and "end_date"'
            }), 400
        
        logger.info(f"Extract topics request: start_date={start_date}, end_date={end_date}")
        
        # Get conversations for the date range
        conversations_by_id = conversation_service.get_conversations_by_date_range(start_date, end_date)
        
        if not conversations_by_id:
            return jsonify({
                'success': True,
                'start_date': start_date,
                'end_date': end_date,
                'processed_count': 0,
                'message': f'No conversations found for date range {start_date} to {end_date}'
            })
        
        # Reset state
        topic_extraction_state.update({
            'is_running': True,
            'current': 0,
            'total': len(conversations_by_id),
            'processed_count': 0,
            'skipped_count': 0,
            'failed_count': 0,
            'start_time': datetime.now(),
            'end_time': None,
            'error': None,
            'progress_percentage': 0,
            'start_date': start_date,
            'end_date': end_date,
            'dates_processed': []
        })
        
        # Start extraction in background thread
        topic_extraction_thread = threading.Thread(
            target=_run_topic_extraction,
            args=(conversation_service, claude_service, start_date, end_date, conversations_by_id),
            daemon=True
        )
        topic_extraction_thread.start()
        
        logger.info(f"Started topic extraction in background thread for {len(conversations_by_id)} conversations")
        
        return jsonify({
            'success': True,
            'message': f'Topic extraction started for {len(conversations_by_id)} conversations. Use /api/conversations/extract-topics-status to check progress.',
            'total': len(conversations_by_id)
        })
    
    except Exception as e:
        logger.error(f"Extract topics error: {str(e)}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        return jsonify({'error': str(e)}), 500


def _update_extraction_progress(current: int, total: int, processed: int, skipped: int, failed: int):
    """Update topic extraction progress state"""
    global topic_extraction_state
    
    topic_extraction_state['current'] = current
    topic_extraction_state['total'] = total
    topic_extraction_state['processed_count'] = processed
    topic_extraction_state['skipped_count'] = skipped
    topic_extraction_state['failed_count'] = failed
    
    # Calculate progress percentage
    if total > 0:
        topic_extraction_state['progress_percentage'] = (current / total) * 100


def _run_topic_extraction(conversation_service, claude_service, start_date: str, end_date: str, conversations_by_id: Dict):
    """Run topic extraction in background thread"""
    global topic_extraction_state
    
    try:
        from ...services.topic_extraction_service import TopicExtractionService
        from ...services.topic_storage_service import TopicStorageService
        
        topic_service = TopicExtractionService(claude_service)
        topic_storage = TopicStorageService()
        
        total_conversations = len(conversations_by_id)
        logger.info(f"Extracting topics for {total_conversations} conversations with rate limiting...")
        
        # Group conversations by date
        from datetime import datetime, timedelta
        conversations_by_date: Dict[str, Dict[str, List[Dict]]] = {}
        for conv_id, items in conversations_by_id.items():
            if items and items[0].get('timestamp'):
                try:
                    item_time = datetime.fromisoformat(items[0]['timestamp'].replace('Z', '+00:00'))
                    item_date_str = item_time.date().isoformat()
                    if item_date_str not in conversations_by_date:
                        conversations_by_date[item_date_str] = {}
                    conversations_by_date[item_date_str][conv_id] = items
                except (ValueError, KeyError):
                    if start_date not in conversations_by_date:
                        conversations_by_date[start_date] = {}
                    conversations_by_date[start_date][conv_id] = items
            else:
                if start_date not in conversations_by_date:
                    conversations_by_date[start_date] = {}
                conversations_by_date[start_date][conv_id] = items
        
        all_extracted_mapping = {}
        dates_processed = []
        total_processed = 0
        total_skipped = 0
        current_count = 0
        
        for date_str, date_conversations in conversations_by_date.items():
            existing_topics = topic_storage.get_topics_for_date(date_str) or {}
            conversations_to_process = {}
            
            for conv_id, items in date_conversations.items():
                current_count += 1
                if conv_id in existing_topics:
                    total_skipped += 1
                    all_extracted_mapping[conv_id] = existing_topics[conv_id]
                else:
                    conversations_to_process[conv_id] = items
                _update_extraction_progress(current_count, total_conversations, total_processed, total_skipped, 0)
            
            if not conversations_to_process:
                dates_processed.append(date_str)
                continue
            
            date_topic_mapping = {}
            date_last_save = 0
            
            def date_incremental_save(conversation_id: str, topic: str):
                nonlocal date_topic_mapping, date_last_save, all_extracted_mapping, total_processed, current_count
                date_topic_mapping[conversation_id] = topic
                all_extracted_mapping[conversation_id] = topic
                total_processed += 1
                current_count += 1
                
                if len(date_topic_mapping) - date_last_save >= 10:
                    try:
                        existing = topic_storage.get_topics_for_date(date_str) or {}
                        existing.update(date_topic_mapping)
                        topic_storage.save_topics_for_date(date_str, existing)
                        date_last_save = len(date_topic_mapping)
                    except Exception as save_error:
                        logger.warning(f"Failed incremental save for {date_str}: {save_error}")
                
                _update_extraction_progress(current_count, total_conversations, total_processed, total_skipped, 0)
            
            extracted_for_date = topic_service.batch_extract_topics(
                conversations_to_process,
                delay_between_requests=0.5,
                incremental_save_callback=date_incremental_save,
                save_every=10
            )
            
            if date_topic_mapping:
                existing = topic_storage.get_topics_for_date(date_str) or {}
                existing.update(date_topic_mapping)
                topic_storage.save_topics_for_date(date_str, existing)
            
            dates_processed.append(date_str)
        
        topic_extraction_state['end_time'] = datetime.now()
        topic_extraction_state['dates_processed'] = dates_processed
        topic_extraction_state['is_running'] = False
        
        logger.info(f"Topic extraction completed: {total_processed} processed, {total_skipped} skipped")
    
    except Exception as e:
        error_msg = str(e)
        logger.error(f"Topic extraction failed: {error_msg}")
        topic_extraction_state['error'] = error_msg
        topic_extraction_state['is_running'] = False
        topic_extraction_state['end_time'] = datetime.now()


@conversation_bp.route('/extract-topics-status', methods=['GET'])
def get_extract_topics_status():
    """Get status of running topic extraction"""
    global topic_extraction_state
    
    try:
        elapsed_time = None
        if topic_extraction_state['start_time']:
            end = topic_extraction_state['end_time'] or datetime.now()
            elapsed_time = (end - topic_extraction_state['start_time']).total_seconds()
        
        return jsonify({
            'success': True,
            'is_running': topic_extraction_state['is_running'],
            'current': topic_extraction_state['current'],
            'total': topic_extraction_state['total'],
            'processed_count': topic_extraction_state['processed_count'],
            'skipped_count': topic_extraction_state['skipped_count'],
            'failed_count': topic_extraction_state['failed_count'],
            'progress_percentage': round(topic_extraction_state['progress_percentage'], 2),
            'start_time': topic_extraction_state['start_time'].isoformat() if topic_extraction_state['start_time'] else None,
            'end_time': topic_extraction_state['end_time'].isoformat() if topic_extraction_state['end_time'] else None,
            'elapsed_time': elapsed_time,
            'error': topic_extraction_state['error'],
            'start_date': topic_extraction_state['start_date'],
            'end_date': topic_extraction_state['end_date'],
            'dates_processed': topic_extraction_state['dates_processed']
        })
    except Exception as e:
        logger.error(f"Get extract topics status error: {e}")
        return jsonify({'error': str(e)}), 500


@conversation_bp.route('/topic-extraction-status', methods=['GET'])
def get_topic_extraction_status():
    """Get status of extracted topics by date"""
    try:
        from ...services.topic_storage_service import TopicStorageService
        
        topic_storage = TopicStorageService()
        status = topic_storage.get_extraction_status()
        
        return jsonify({
            'success': True,
            'status': status,
            'total_dates': len(status)
        })
    
    except Exception as e:
        logger.error(f"Topic extraction status error: {str(e)}")
        return jsonify({'error': str(e)}), 500


@conversation_bp.route('/conversation-count', methods=['GET'])
def get_conversation_count():
    """Get count of conversations for a specific date or date range"""
    try:
        # Get service from container (injected via Flask's g)
        service_container = getattr(g, 'service_container', None)
        if not service_container:
            logger.error("Service container not available in request context")
            return jsonify({'error': 'Service container not initialized'}), 500
        
        conversation_service = service_container.get_conversation_service()
        
        # Get date parameters
        date = request.args.get('date')
        start_date = request.args.get('start_date', date)
        end_date = request.args.get('end_date', date)
        
        if not start_date or not end_date:
            return jsonify({
                'success': False,
                'error': 'Missing date parameters',
                'details': 'Please provide either "date" or both "start_date" and "end_date"'
            }), 400
        
        # Get conversations for the date range
        conversations_by_id = conversation_service.get_conversations_by_date_range(start_date, end_date)
        count = len(conversations_by_id)
        
        return jsonify({
            'success': True,
            'start_date': start_date,
            'end_date': end_date,
            'count': count
        })
    
    except Exception as e:
        logger.error(f"Get conversation count error: {str(e)}")
        return jsonify({'error': str(e)}), 500


@conversation_bp.route('/topic-trends-over-time', methods=['GET'])
def get_topic_trends_over_time():
    """Get topic trends over a date range (for time-series chart)"""
    try:
        from ...services.topic_storage_service import TopicStorageService
        
        # Get date range parameters
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        
        if not start_date or not end_date:
            return jsonify({
                'success': False,
                'error': 'Missing date parameters',
                'details': 'Please provide both "start_date" and "end_date"'
            }), 400
        
        topic_storage = TopicStorageService()
        
        # Get all dates in range that have extracted topics
        from datetime import datetime, timedelta
        start = datetime.strptime(start_date, '%Y-%m-%d').date()
        end = datetime.strptime(end_date, '%Y-%m-%d').date()
        
        # Get all available dates from storage
        status = topic_storage.get_extraction_status()
        all_topics = topic_storage.topics_by_date
        
        # Filter dates in range
        dates_in_range = []
        current_date = start
        while current_date <= end:
            date_str = current_date.isoformat()
            if date_str in all_topics:
                dates_in_range.append(date_str)
            current_date += timedelta(days=1)
        
        if not dates_in_range:
            return jsonify({
                'success': False,
                'start_date': start_date,
                'end_date': end_date,
                'data': [],
                'message': f'No topics extracted for date range {start_date} to {end_date}'
            })
        
        # Aggregate topics by date
        all_topics_set = set()
        date_topic_data = {}
        
        for date_str in dates_in_range:
            topic_mapping = all_topics.get(date_str, {})
            topic_counts = {}
            for conversation_id, topic in topic_mapping.items():
                topic_counts[topic] = topic_counts.get(topic, 0) + 1
                all_topics_set.add(topic)
            
            date_topic_data[date_str] = topic_counts
        
        # Build data structure for stacked bar chart
        # Format: [{ date: '2025-10-20', 'Topic1': 10, 'Topic2': 5, ... }, ...]
        chart_data = []
        sorted_topics = sorted(all_topics_set)
        
        for date_str in sorted(dates_in_range):
            date_data = {'date': date_str}
            topic_counts = date_topic_data.get(date_str, {})
            total = sum(topic_counts.values())
            
            for topic in sorted_topics:
                count = topic_counts.get(topic, 0)
                percentage = (count / total * 100) if total > 0 else 0
                date_data[topic] = count  # Use count for stacked bar
                date_data[f'{topic}_percentage'] = round(percentage, 2)
            
            date_data['total'] = total
            chart_data.append(date_data)
        
        return jsonify({
            'success': True,
            'start_date': start_date,
            'end_date': end_date,
            'topics': sorted_topics,
            'data': chart_data,
            'dates': dates_in_range
        })
    
    except Exception as e:
        logger.error(f"Topic trends over time error: {str(e)}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        return jsonify({'error': str(e)}), 500