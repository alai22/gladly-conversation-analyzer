# Multi-stage Dockerfile for Gladly Web Interface
FROM node:18-alpine as frontend-build

WORKDIR /app
COPY package*.json ./
RUN npm ci --only=production
COPY src/ ./src/
COPY public/ ./public/
COPY tailwind.config.js postcss.config.js ./
RUN npm run build

FROM python:3.11-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    FLASK_ENV=production \
    FLASK_DEBUG=0

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user
RUN adduser --disabled-password --gecos '' appuser

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy Python application
COPY *.py ./
COPY config_cloud.py ./config_local.py

# Copy built React app
COPY --from=frontend-build /app/build ./build

# Create serve.py for unified Flask app
RUN cat > serve.py << 'EOF'
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
EOF

# Change ownership to appuser
RUN chown -R appuser:appuser /app

# Switch to non-root user
USER appuser

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:5000/health || exit 1

EXPOSE 5000
CMD ["python", "serve.py"]