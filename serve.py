from flask import Flask, send_from_directory
from flask_cors import CORS
import os
from app import app as api_app

app = Flask(__name__, static_folder="build")

# Enable CORS for all origins in production
CORS(app)

# Mount API routes
app.register_blueprint(api_app)

@app.route("/", defaults={"path": ""})
@app.route("/<path:path>")
def serve(path):
    if path != "" and os.path.exists(os.path.join(app.static_folder, path)):
        return send_from_directory(app.static_folder, path)
    else:
        return send_from_directory(app.static_folder, "index.html")

@app.route("/health")
def health_check():
    return {"status": "ok", "service": "gladly-conversation-analyzer"}

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    host = os.environ.get("HOST", "0.0.0.0")
    
    print(f"Starting Gladly Conversation Analyzer on {host}:{port}")
    app.run(host=host, port=port, debug=False)
