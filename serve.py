from flask import Flask, send_from_directory
from flask_cors import CORS
import os
from app import app as api_app

# Create main app
app = Flask(__name__, static_folder="build")

# Enable CORS for all origins in production
CORS(app)

# Copy only the API routes from api_app, excluding built-in Flask routes
for rule in api_app.url_map.iter_rules():
    # Skip built-in Flask routes like 'static'
    if rule.endpoint not in ['static']:
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
    app.run(host=host, port=port, debug=False)
