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
    """Get conversation topic trends for a specific date"""
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
        
        # Get date parameter (default to 2025-10-20 for prototype)
        date = request.args.get('date', '2025-10-20')
        
        logger.info(f"Topic trends request: date={date}")
        
        # Get conversations for the date
        conversations_by_id = conversation_service.get_conversations_by_date(date)
        
        if not conversations_by_id:
            return jsonify({
                'success': True,
                'date': date,
                'topics': [],
                'data': [],
                'total': 0,
                'message': f'No conversations found for date {date}'
            })
        
        # Import topic extraction service
        from ...services.topic_extraction_service import TopicExtractionService
        
        # Initialize topic extraction service
        topic_service = TopicExtractionService(claude_service)
        
        # Extract topics for all conversations
        logger.info(f"Extracting topics for {len(conversations_by_id)} conversations...")
        topic_mapping = topic_service.batch_extract_topics(conversations_by_id)
        
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
        
        # Import topic extraction service
        from ...services.topic_extraction_service import TopicExtractionService
        
        # Initialize topic extraction service
        topic_service = TopicExtractionService(claude_service)
        
        # Extract topics for all conversations
        logger.info(f"Extracting topics for {len(conversations_by_id)} conversations...")
        topic_mapping = topic_service.batch_extract_topics(conversations_by_id)
        
        processed_count = len(topic_mapping)
        
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
        logger.error(f"Extract topics error: {str(e)}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        return jsonify({'error': str(e)}), 500