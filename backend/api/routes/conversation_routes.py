"""
API routes for conversation data interactions
"""

from flask import Blueprint, request, jsonify
from ...services.conversation_service import ConversationService
from ...models.response import SearchResult
from ...utils.logging import get_logger

logger = get_logger('conversation_routes')

# Create blueprint
conversation_bp = Blueprint('conversations', __name__, url_prefix='/api/conversations')

# Initialize service
conversation_service = ConversationService()


@conversation_bp.route('/summary')
def conversations_summary():
    """Get conversation data summary"""
    try:
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
