"""
API routes for RAG-powered analysis
"""

from flask import Blueprint, request, jsonify, g
from ...utils.logging import get_logger

logger = get_logger('rag_routes')

# Create blueprint
rag_bp = Blueprint('rag', __name__, url_prefix='/api/conversations')


@rag_bp.route('/ask', methods=['POST'])
def conversations_ask():
    """Ask Claude about conversation data with detailed RAG process information"""
    try:
        # Get services from container (injected via Flask's g)
        # Use getattr with default None to avoid AttributeError
        service_container = getattr(g, 'service_container', None)
        if not service_container:
            logger.error("Service container not available in request context")
            return jsonify({'error': 'Service container not initialized'}), 500
        
        claude_service = service_container.get_claude_service()
        rag_service = service_container.get_rag_service()
        
        data = request.get_json()
        question = data.get('question')
        model = data.get('model', 'claude-sonnet-4')  # Default to Sonnet 4 (non-dated alias)
        max_tokens = data.get('max_tokens', 2000)
        
        if not question:
            return jsonify({'error': 'Question is required'}), 400
        
        logger.info(f"RAG query request: question={question[:100]}, model={model}, max_tokens={max_tokens}")
        
        # Check if Claude service is initialized
        if claude_service is None or rag_service is None:
            error_msg = "Claude API service is not initialized. Please check ANTHROPIC_API_KEY configuration."
            logger.error(error_msg)
            return jsonify({
                'error': error_msg, 
                'details': 'ANTHROPIC_API_KEY environment variable is not set or invalid. Please configure it in your .env file or environment.'
            }), 503
        
        # Skip aggressive availability check - let the actual API call handle errors
        # The is_available() check makes an HTTP request which can fail due to network issues
        # and is not a reliable indicator. We'll let the actual API call fail gracefully if needed.
        
        result = rag_service.process_query(question, model, max_tokens)
        
        return jsonify(result)
    
    except TimeoutError as e:
        # Handle timeout errors specifically
        error_msg = str(e) if str(e) else "Request to Claude API timed out. The query may be too complex."
        logger.error(f"RAG query timeout: {error_msg}")
        return jsonify({
            'error': 'Request timeout',
            'details': error_msg,
            'type': 'TimeoutError',
            'suggestion': 'Try simplifying your query or increasing CLAUDE_API_TIMEOUT if needed.'
        }), 504  # 504 Gateway Timeout
    
    except ValueError as e:
        # Handle configuration errors (e.g., missing API key)
        error_msg = f"Configuration error: {str(e)}"
        logger.error(error_msg)
        return jsonify({'error': error_msg, 'details': 'Please check your API configuration (ANTHROPIC_API_KEY)'}), 500
    except Exception as e:
        # Log full exception for debugging
        import traceback
        logger.error(f"RAG query error: {str(e)}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        
        # Provide more detailed error information
        error_details = str(e)
        if hasattr(e, 'response') and hasattr(e.response, 'text'):
            error_details = f"{str(e)} - Response: {e.response.text}"
        
        return jsonify({
            'error': str(e),
            'details': error_details,
            'type': type(e).__name__
        }), 500

@rag_bp.route('/refresh', methods=['POST'])
def refresh_conversations():
    """Refresh conversation data from storage"""
    try:
        # Get service from container (injected via Flask's g)
        service_container = g.get('service_container')
        if not service_container:
            logger.error("Service container not available in request context")
            return jsonify({'status': 'error', 'message': 'Service container not initialized'}), 500
        
        conversation_service = service_container.get_conversation_service()
        
        logger.info("Refreshing conversation data for RAG system")
        conversation_service.refresh_conversations()
        
        return jsonify({
            'status': 'success',
            'message': f'Conversation data refreshed: {len(conversation_service.conversations)} conversations loaded',
            'data': {
                'total_conversations': len(conversation_service.conversations),
                'is_available': conversation_service.is_available()
            }
        })
    
    except Exception as e:
        logger.error(f"Error refreshing conversations: {str(e)}")
        return jsonify({'status': 'error', 'message': str(e)}), 500