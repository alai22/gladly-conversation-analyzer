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
    logger.info("[HEALTH CHECK] Starting health check request")
    try:
        # Get services from container (injected via Flask's g)
        # Use getattr with default None to avoid AttributeError
        logger.debug(f"[HEALTH CHECK] Getting service container from g: {hasattr(g, 'service_container')}")
        service_container = getattr(g, 'service_container', None)
        logger.debug(f"[HEALTH CHECK] Service container: {service_container is not None}")
        if not service_container:
            logger.error("Service container not available in request context")
            return jsonify({
                'status': 'unhealthy',
                'error': 'Service container not initialized',
                'claude_initialized': False,
                'conversation_analyzer_initialized': False
            }), 200  # Return 200 with unhealthy status in body
        
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
            }), 200  # Return 200 with unhealthy status in body
        
        # Check if services are initialized (don't make external HTTP calls)
        # Making HTTP calls in health checks can cause timeouts and weird errors
        claude_initialized = claude_service is not None
        conversation_initialized = conversation_service is not None
        
        # Check conversation availability (in-memory check, no external calls)
        try:
            conversation_available = conversation_service.is_available()
        except Exception as e:
            logger.error(f"Conversation service availability check failed: {str(e)}")
            conversation_available = False
        
        # Don't call claude_service.is_available() here - it makes external HTTP requests
        # which can fail for network reasons and don't indicate actual service health
        # Instead, just check if the service is initialized
        status = 'healthy' if claude_initialized and conversation_available else 'unhealthy'
        
        response_data = {
            'status': status,
            'claude_initialized': claude_initialized,
            'conversation_analyzer_initialized': conversation_available,
            'error': 'ClaudeService not initialized - check ANTHROPIC_API_KEY' if not claude_initialized else None
        }
        
        logger.info(f"[HEALTH CHECK] Health check completed: status={status}, claude={claude_initialized}, conversations={conversation_available}")
        logger.debug(f"[HEALTH CHECK] Response data: {response_data}")
        
        return jsonify(response_data), 200  # Always return 200, let the status field indicate health
    
    except Exception as e:
        logger.error(f"Health check error: {str(e)}", exc_info=True)
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        return jsonify({
            'status': 'unhealthy',
            'error': str(e),
            'claude_initialized': False,
            'conversation_analyzer_initialized': False
        }), 200  # Always return 200, let status field indicate health
