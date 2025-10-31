"""
API routes for Claude interactions
"""

from flask import Blueprint, request, jsonify, g
from ...utils.logging import get_logger

logger = get_logger('claude_routes')

# Create blueprint
claude_bp = Blueprint('claude', __name__, url_prefix='/api/claude')


@claude_bp.route('/chat', methods=['POST'])
def claude_chat():
    """Send message to Claude API"""
    try:
        # Get service from container (injected via Flask's g)
        # Use getattr with default None to avoid AttributeError
        service_container = getattr(g, 'service_container', None)
        if not service_container:
            logger.error("Service container not available in request context")
            return jsonify({
                'error': 'Service container not initialized',
                'details': 'Internal server error: service container unavailable'
            }), 500
        
        claude_service = service_container.get_claude_service()
        
        # Check if Claude service is initialized
        if claude_service is None:
            error_msg = "Claude API service is not initialized. Please check ANTHROPIC_API_KEY configuration."
            logger.error(error_msg)
            return jsonify({
                'error': error_msg,
                'details': 'ANTHROPIC_API_KEY environment variable is not set or invalid. Please configure it in your .env file or environment.'
            }), 503
        
        data = request.get_json()
        message = data.get('message')
        model = data.get('model', 'claude-sonnet-4')  # Default to Sonnet 4 (non-dated alias)
        max_tokens = data.get('max_tokens', 1000)
        system_prompt = data.get('system_prompt')
        stream = data.get('stream', False)
        
        if not message:
            return jsonify({'error': 'Message is required'}), 400
        
        logger.info(f"Claude chat request: model={model}, max_tokens={max_tokens}, stream={stream}")
        
        if stream:
            # For streaming, we'll collect all chunks and return them
            chunks = []
            for chunk in claude_service.stream_message(
                message=message,
                model=model,
                max_tokens=max_tokens,
                system_prompt=system_prompt
            ):
                chunks.append(chunk)
            
            return jsonify({
                'success': True,
                'response': chunks,
                'streamed': True
            })
        else:
            response = claude_service.send_message(
                message=message,
                model=model,
                max_tokens=max_tokens,
                system_prompt=system_prompt
            )
            
            return jsonify({
                'success': True,
                'response': {
                    'content': [{'type': 'text', 'text': response.content}],
                    'usage': {'output_tokens': response.tokens_used}
                },
                'streamed': False
            })
    
    except Exception as e:
        logger.error(f"Claude chat error: {str(e)}")
        return jsonify({'error': str(e)}), 500
