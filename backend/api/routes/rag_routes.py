"""
API routes for RAG-powered analysis
"""

from flask import Blueprint, request, jsonify
from ...services.rag_service import RAGService
from ...services.claude_service import ClaudeService
from ...services.conversation_service import ConversationService
from ...utils.logging import get_logger

logger = get_logger('rag_routes')

# Create blueprint
rag_bp = Blueprint('rag', __name__, url_prefix='/api/conversations')

# Initialize services with error handling
try:
    claude_service = ClaudeService()
except Exception as e:
    logger.error(f"Failed to initialize ClaudeService: {str(e)}")
    claude_service = None

conversation_service = ConversationService()

# Initialize RAG service only if Claude service is available
if claude_service is not None:
    rag_service = RAGService(claude_service, conversation_service)
else:
    rag_service = None
    logger.warning("RAGService not initialized - ClaudeService unavailable")


@rag_bp.route('/ask', methods=['POST'])
def conversations_ask():
    """Ask Claude about conversation data with detailed RAG process information"""
    try:
        data = request.get_json()
        question = data.get('question')
        model = data.get('model', 'claude-3-opus-20240229')
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
        
        # Check if Claude service is available before processing
        try:
            if not claude_service.is_available():
                error_msg = "Claude API is not available. Please check ANTHROPIC_API_KEY configuration."
                logger.error(error_msg)
                return jsonify({'error': error_msg, 'details': 'Claude API health check failed. Verify API key is set correctly and has proper permissions.'}), 503
        except Exception as e:
            error_msg = f"Claude API availability check failed: {str(e)}"
            logger.error(error_msg)
            return jsonify({'error': error_msg, 'details': 'Unable to verify Claude API connection. Check API key and network connectivity.'}), 503
        
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