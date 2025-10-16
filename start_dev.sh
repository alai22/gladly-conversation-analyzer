#!/bin/bash

# Gladly Web Interface Development Startup Script

echo "🚀 Starting Gladly Web Interface Development Environment"
echo "=================================================="

# Check if config_local.py exists
if [ ! -f "config_local.py" ]; then
    echo "⚠️  WARNING: config_local.py not found!"
    echo "Please copy config.py to config_local.py and add your API key."
    echo ""
    echo "To fix this:"
    echo "1. cp config.py config_local.py"
    echo "2. Edit config_local.py and replace 'your-api-key-here' with your real API key"
    echo ""
    read -p "Press Enter to continue anyway (backend will fail to start)..."
fi

# Check if conversation data exists
if [ ! -f "conversation_items.jsonl" ]; then
    echo "⚠️  WARNING: conversation_items.jsonl not found!"
    echo "The conversation analysis features will not work without this file."
    echo ""
fi

# Create virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    echo "📦 Creating Python virtual environment..."
    python3 -m venv venv
fi

# Install Python dependencies
echo "📦 Installing Python dependencies..."
source venv/bin/activate
pip install -r requirements.txt

# Install Node.js dependencies
echo "📦 Installing Node.js dependencies..."
npm install

echo ""
echo "✅ Setup complete!"
echo ""
echo "To start the development environment:"
echo "1. Run: npm run dev"
echo "   This will start both the React frontend (localhost:3000) and Flask backend (localhost:5000)"
echo ""
echo "2. Or start them separately:"
echo "   Frontend: npm start"
echo "   Backend:  source venv/bin/activate && python app.py"
echo ""
echo "🌐 The web interface will be available at: http://localhost:3000"
echo "🔧 The API backend will be available at: http://localhost:5000"
echo ""
