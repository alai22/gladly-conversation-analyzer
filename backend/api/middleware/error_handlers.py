"""
Error handling middleware
"""

from flask import jsonify
from ...utils.logging import get_logger

logger = get_logger('error_handlers')


def register_error_handlers(app):
    """Register error handlers for the Flask app"""
    
    @app.errorhandler(400)
    def bad_request(error):
        logger.warning("Bad request", error=str(error))
        return jsonify({'error': 'Bad request'}), 400
    
    @app.errorhandler(401)
    def unauthorized(error):
        logger.warning("Unauthorized request", error=str(error))
        return jsonify({'error': 'Unauthorized'}), 401
    
    @app.errorhandler(404)
    def not_found(error):
        logger.warning("Not found", error=str(error))
        return jsonify({'error': 'Not found'}), 404
    
    @app.errorhandler(500)
    def internal_error(error):
        logger.error("Internal server error", error=str(error))
        return jsonify({'error': 'Internal server error'}), 500
    
    @app.errorhandler(Exception)
    def handle_exception(error):
        logger.error("Unhandled exception", error=str(error))
        return jsonify({'error': 'An unexpected error occurred'}), 500
