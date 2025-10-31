"""
Health check routes
"""

from flask import Blueprint, jsonify, g
from ...utils.logging import get_logger

logger = get_logger('health_routes')

# Create blueprint
health_bp = Blueprint('health', __name__, url_prefix='/api')


@health_bp.route('/health')
def health_check():
    """Health check endpoint"""
    try:
        # Get services from container (injected via Flask's g)
        # Use getattr with default None to avoid AttributeError
        service_container = getattr(g, 'service_container', None)
        if not service_container:
            logger.error("Service container not available in request context")
            return jsonify({
                'status': 'unhealthy',
                'error': 'Service container not initialized',
                'claude_initialized': False,
                'conversation_analyzer_initialized': False
            }), 500
        
        try:
            claude_service = service_container.get_claude_service()
            conversation_service = service_container.get_conversation_service()
        except Exception as e:
            logger.error(f"Failed to get services from container: {str(e)}", exc_info=True)
            return jsonify({
                'status': 'unhealthy',
                'error': f'Failed to get services: {str(e)}',
                'claude_initialized': False,
                'conversation_analyzer_initialized': False
            }), 500
        
        claude_available = False
        if claude_service is not None:
            try:
                claude_available = claude_service.is_available()
            except Exception as e:
                logger.error(f"Claude availability check failed: {str(e)}")
                claude_available = False
        else:
            logger.warning("ClaudeService not initialized - check ANTHROPIC_API_KEY")
        
        try:
            conversation_available = conversation_service.is_available()
        except Exception as e:
            logger.error(f"Conversation service availability check failed: {str(e)}")
            conversation_available = False
        
        status = 'healthy' if claude_available and conversation_available else 'unhealthy'
        
        return jsonify({
            'status': status,
            'claude_initialized': claude_available,
            'conversation_analyzer_initialized': conversation_available,
            'error': 'ClaudeService not initialized - check ANTHROPIC_API_KEY' if claude_service is None else None
        })
    
    except Exception as e:
        logger.error(f"Health check error: {str(e)}", exc_info=True)
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        return jsonify({
            'status': 'unhealthy',
            'error': str(e),
            'claude_initialized': False,
            'conversation_analyzer_initialized': False
        }), 500
