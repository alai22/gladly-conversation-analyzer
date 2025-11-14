"""
API routes for conversation data interactions
"""

from flask import Blueprint, request, jsonify, g
from ...models.response import SearchResult
from ...utils.logging import get_logger

logger = get_logger('conversation_routes')

# Create blueprint
conversation_bp = Blueprint('conversations', __name__, url_prefix='/api/conversations')


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
    """Extract topics from conversations for a specific date (pre-processing for trends)"""
    try:
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
        
        # Get date parameter from request body
        data = request.get_json() or {}
        date = data.get('date', '2025-10-20')
        
        logger.info(f"Extract topics request: date={date}")
        
        # Get conversations for the date
        conversations_by_id = conversation_service.get_conversations_by_date(date)
        
        if not conversations_by_id:
            return jsonify({
                'success': True,
                'date': date,
                'processed_count': 0,
                'message': f'No conversations found for date {date}'
            })
        
        # Import services
        from ...services.topic_extraction_service import TopicExtractionService
        from ...services.topic_storage_service import TopicStorageService
        
        # Initialize services
        topic_service = TopicExtractionService(claude_service)
        topic_storage = TopicStorageService()
        
        # Extract topics for all conversations with rate limiting
        # Use 0.5 second delay between requests to avoid rate limits
        # Claude allows 200k input tokens/minute, so we need to pace requests
        logger.info(f"Extracting topics for {len(conversations_by_id)} conversations with rate limiting...")
        
        try:
            topic_mapping = topic_service.batch_extract_topics(
                conversations_by_id,
                delay_between_requests=0.5  # 0.5 second delay = ~120 requests/minute max
            )
            
            processed_count = len(topic_mapping)
            
            # Save topics to storage
            topic_storage.save_topics_for_date(date, topic_mapping)
            
            # Count topics for summary
            topic_counts = {}
            for conversation_id, topic in topic_mapping.items():
                topic_counts[topic] = topic_counts.get(topic, 0) + 1
            
            logger.info(f"Topic extraction completed: {processed_count} conversations processed, {len(topic_counts)} unique topics")
            
            return jsonify({
                'success': True,
                'date': date,
                'processed_count': processed_count,
                'topic_summary': topic_counts,
                'message': f'Successfully extracted topics for {processed_count} conversations'
            })
        
        except Exception as e:
            error_msg = str(e)
            logger.error(f"Topic extraction failed: {error_msg}")
            
            # Provide more helpful error messages
            if '429' in error_msg or 'rate_limit' in error_msg.lower() or 'Too Many Requests' in error_msg:
                return jsonify({
                    'success': False,
                    'error': 'Rate limit exceeded',
                    'details': 'Claude API rate limit reached. Please wait 1-2 minutes and try again. The system processes conversations with delays to avoid rate limits, but large batches may still hit limits.',
                    'message': error_msg
                }), 429
            elif 'timeout' in error_msg.lower() or '504' in error_msg:
                return jsonify({
                    'success': False,
                    'error': 'Request timeout',
                    'details': 'The request took too long to complete. This can happen with large batches. Try processing fewer conversations at once or wait and try again.',
                    'message': error_msg
                }), 504
            else:
                return jsonify({
                    'success': False,
                    'error': 'Extraction failed',
                    'details': error_msg,
                    'message': f'Failed to extract topics: {error_msg}'
                }), 500
    
    except Exception as e:
        logger.error(f"Extract topics error: {str(e)}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
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