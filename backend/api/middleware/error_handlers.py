"""
Error handling middleware
"""

from flask import jsonify, request
from ...utils.logging import get_logger
import traceback

logger = get_logger('error_handlers')


def register_error_handlers(app):
    """Register error handlers for the Flask app"""
    
    @app.errorhandler(400)
    def bad_request(error):
        logger.warning(f"[ERROR HANDLER] Bad request (400): {str(error)} | Path: {request.path}")
        return jsonify({'error': 'Bad request', 'status_code': 400}), 400
    
    @app.errorhandler(401)
    def unauthorized(error):
        logger.warning(f"[ERROR HANDLER] Unauthorized (401): {str(error)} | Path: {request.path}")
        return jsonify({'error': 'Unauthorized', 'status_code': 401}), 401
    
    @app.errorhandler(404)
    def not_found(error):
        logger.warning(f"[ERROR HANDLER] Not found (404): {str(error)} | Path: {request.path}")
        return jsonify({'error': 'Not found', 'status_code': 404}), 404
    
    @app.errorhandler(431)
    def request_header_fields_too_large(error):
        logger.error(f"[ERROR HANDLER] Request Header Fields Too Large (431): {str(error)} | Path: {request.path}")
        logger.error(f"[ERROR HANDLER] Request headers size: {sum(len(k) + len(v) for k, v in request.headers.items())} bytes")
        return jsonify({
            'error': 'Request header fields too large', 
            'status_code': 431,
            'details': 'The request headers exceed the maximum size allowed by the server.'
        }), 431
    
    @app.errorhandler(500)
    def internal_error(error):
        logger.error(f"[ERROR HANDLER] Internal server error (500): {str(error)} | Path: {request.path}")
        logger.error(f"[ERROR HANDLER] Traceback: {traceback.format_exc()}")
        return jsonify({'error': 'Internal server error', 'status_code': 500}), 500
    
    @app.errorhandler(Exception)
    def handle_exception(error):
        logger.error(f"[ERROR HANDLER] Unhandled exception: {type(error).__name__}: {str(error)} | Path: {request.path}")
        logger.error(f"[ERROR HANDLER] Traceback: {traceback.format_exc()}")
        return jsonify({
            'error': 'An unexpected error occurred',
            'error_type': type(error).__name__,
            'status_code': 500
        }), 500
