# IMPORTANT: Set Werkzeug max header size BEFORE importing Flask
# This must be done before Flask/Werkzeug initializes the request handler
import werkzeug.serving
werkzeug.serving.WSGIRequestHandler.max_header_size = 32768  # 32KB (default is 8KB)

from flask import Flask, send_from_directory
from flask_cors import CORS
import os
from app import app as api_app

# Initialize services (they initialize themselves when imported)
print("Initializing services...")
try:
    from backend.services.claude_service import ClaudeService
    from backend.services.conversation_service import ConversationService
    print("✅ Services initialized successfully")
except Exception as e:
    print(f"⚠️ Warning: Failed to initialize services: {e}")

# Create main app
app = Flask(__name__, static_folder="build")

# Enable CORS for all origins in production
CORS(app)

# Copy only the API routes from api_app, excluding built-in Flask routes and root route
for rule in api_app.url_map.iter_rules():
    # Skip built-in Flask routes like 'static' and the root route '/'
    if rule.endpoint not in ['static', 'index']:
        app.add_url_rule(
            rule.rule,
            endpoint=rule.endpoint,
            view_func=api_app.view_functions[rule.endpoint],
            methods=rule.methods
        )

@app.route("/", defaults={"path": ""})
@app.route("/<path:path>")
def serve(path):
    if path != "" and os.path.exists(os.path.join(app.static_folder, path)):
        return send_from_directory(app.static_folder, path)
    else:
        return send_from_directory(app.static_folder, "index.html")

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    host = os.environ.get("HOST", "0.0.0.0")
    
    print(f"Starting Gladly Conversation Analyzer on {host}:{port}")
    print(f"Max header size: {werkzeug.serving.WSGIRequestHandler.max_header_size} bytes")
    app.run(host=host, port=port, debug=False)
