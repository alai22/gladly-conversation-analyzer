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

# Initialize services
claude_service = ClaudeService()
conversation_service = ConversationService()
rag_service = RAGService(claude_service, conversation_service)


@rag_bp.route('/ask', methods=['POST'])
def conversations_ask():
    """Ask Claude about conversation data with detailed RAG process information"""
    try:
        data = request.get_json()
        question = data.get('question')
        model = data.get('model', 'claude-3-5-sonnet-20241022')
        max_tokens = data.get('max_tokens', 2000)
        
        if not question:
            return jsonify({'error': 'Question is required'}), 400
        
        logger.info(f"RAG query request: question={question[:100]}, model={model}, max_tokens={max_tokens}")
        
        result = rag_service.process_query(question, model, max_tokens)
        
        return jsonify(result)
    
    except Exception as e:
        logger.error(f"RAG query error: {str(e)}")
        return jsonify({'error': str(e)}), 500

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