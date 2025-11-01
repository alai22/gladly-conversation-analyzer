"""
Modular Flask application for Gladly Conversation Analyzer
"""

# IMPORTANT: Set Werkzeug max header size BEFORE importing Flask
# This must be done before Flask/Werkzeug initializes the request handler
import werkzeug.serving
werkzeug.serving.WSGIRequestHandler.max_header_size = 32768  # 32KB (default is 8KB)

# Verify and print the setting
print(f"[FLASK CONFIG] Max header size configured: {werkzeug.serving.WSGIRequestHandler.max_header_size} bytes")

from flask import Flask, render_template_string
from flask_cors import CORS
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Import blueprints
from backend.api.routes.claude_routes import claude_bp
from backend.api.routes.conversation_routes import conversation_bp
from backend.api.routes.rag_routes import rag_bp
from backend.api.routes.health_routes import health_bp
from backend.api.routes.download_routes import download_bp

# Import middleware
from backend.api.middleware.error_handlers import register_error_handlers
from backend.api.middleware.request_logging import register_request_logging

# Import utilities
from backend.utils.config import Config
from backend.utils.logging import setup_logging, get_logger
from backend.core.service_container import ServiceContainer

# Setup logging
logger = setup_logging()
app_logger = get_logger('app')

# Create global service container
_service_container = None

def get_service_container() -> ServiceContainer:
    """Get the global service container instance"""
    global _service_container
    if _service_container is None:
        _service_container = ServiceContainer()
        app_logger.info("Service container created")
    return _service_container

def create_app():
    """Create and configure the Flask application"""
    
    # Validate configuration
    if not Config.validate():
        app_logger.warning("Configuration validation failed, some features may not work")
    
    # Create Flask app
    app = Flask(__name__)
    
    # Enable CORS
    CORS(app)
    
    # Register request logging FIRST (so it logs all requests)
    register_request_logging(app)
    
    # Initialize service container and make it available via Flask's g
    from flask import g
    
    @app.before_request
    def before_request():
        """Initialize service container for each request"""
        try:
            g.service_container = get_service_container()
        except Exception as e:
            app_logger.error(f"Failed to initialize service container in before_request: {str(e)}", exc_info=True)
            # Set to None so routes can handle gracefully
            g.service_container = None
    
    # Register blueprints
    app.register_blueprint(health_bp)
    app.register_blueprint(claude_bp)
    app.register_blueprint(conversation_bp)
    app.register_blueprint(rag_bp)
    app.register_blueprint(download_bp)
    
    # Register error handlers
    register_error_handlers(app)
    
    # Root route - serve React app
    @app.route('/')
    def index():
        """Serve the React app"""
        return render_template_string("""
        <!DOCTYPE html>
        <html lang="en">
        <head>
            <meta charset="utf-8" />
            <meta name="viewport" content="width=device-width, initial-scale=1" />
            <meta name="theme-color" content="#000000" />
            <meta name="description" content="Gladly AI Analysis Interface" />
            <title>Gladly AI Analyzer</title>
        </head>
        <body>
            <noscript>You need to enable JavaScript to run this app.</noscript>
            <div id="root"></div>
        </body>
        </html>
        """)
    
    app_logger.info("Flask application created successfully")
    return app


# Create the app instance
app = create_app()

if __name__ == '__main__':
    app_logger.info("Starting Gladly Web Interface...")
    app_logger.info(f"Starting Flask server on http://{Config.HOST}:{Config.PORT}")
    app_logger.info(f"[OK] Max header size: {werkzeug.serving.WSGIRequestHandler.max_header_size} bytes (was 8192)")
    app.run(debug=Config.FLASK_DEBUG, host=Config.HOST, port=Config.PORT)
