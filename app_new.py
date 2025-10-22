"""
Modular Flask application for Gladly Conversation Analyzer
"""

from flask import Flask, render_template_string
from flask_cors import CORS
import os

# Import blueprints
from backend.api.routes.claude_routes import claude_bp
from backend.api.routes.conversation_routes import conversation_bp
from backend.api.routes.rag_routes import rag_bp
from backend.api.routes.health_routes import health_bp

# Import middleware
from backend.api.middleware.error_handlers import register_error_handlers

# Import utilities
from backend.utils.config import Config
from backend.utils.logging import setup_logging, get_logger

# Setup logging
logger = setup_logging()
app_logger = get_logger('app')

def create_app():
    """Create and configure the Flask application"""
    
    # Validate configuration
    if not Config.validate():
        app_logger.warning("Configuration validation failed, some features may not work")
    
    # Create Flask app
    app = Flask(__name__)
    
    # Enable CORS
    CORS(app)
    
    # Register blueprints
    app.register_blueprint(health_bp)
    app.register_blueprint(claude_bp)
    app.register_blueprint(conversation_bp)
    app.register_blueprint(rag_bp)
    
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
            <meta name="description" content="Gladly Conversation Testing Interface" />
            <title>Gladly Conversation Tester</title>
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
    app_logger.info(f"🚀 Starting Flask server on http://{Config.HOST}:{Config.PORT}")
    app.run(debug=Config.FLASK_DEBUG, host=Config.HOST, port=Config.PORT)
