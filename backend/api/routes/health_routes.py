"""
Health check routes
"""

from flask import Blueprint, jsonify
from ...services.claude_service import ClaudeService
from ...services.conversation_service import ConversationService
from ...utils.logging import get_logger

logger = get_logger('health_routes')

# Create blueprint
health_bp = Blueprint('health', __name__, url_prefix='/api')

# Initialize services with error handling
try:
    claude_service = ClaudeService()
except Exception as e:
    logger.error(f"Failed to initialize ClaudeService: {str(e)}")
    claude_service = None

conversation_service = ConversationService()


@health_bp.route('/health')
def health_check():
    """Health check endpoint"""
    try:
        claude_available = False
        if claude_service is not None:
            try:
                claude_available = claude_service.is_available()
            except Exception as e:
                logger.error(f"Claude availability check failed: {str(e)}")
                claude_available = False
        else:
            logger.warning("ClaudeService not initialized - check ANTHROPIC_API_KEY")
        
        conversation_available = conversation_service.is_available()
        
        status = 'healthy' if claude_available and conversation_available else 'unhealthy'
        
        return jsonify({
            'status': status,
            'claude_initialized': claude_available,
            'conversation_analyzer_initialized': conversation_available,
            'error': 'ClaudeService not initialized - check ANTHROPIC_API_KEY' if claude_service is None else None
        })
    
    except Exception as e:
        logger.error(f"Health check error: {str(e)}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        return jsonify({
            'status': 'unhealthy',
            'error': str(e)
        }), 500
