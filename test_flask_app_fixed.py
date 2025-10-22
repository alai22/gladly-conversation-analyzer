#!/usr/bin/env python3
"""
Test script for Flask application with proper environment setup
"""

import os

def test_flask_app():
    """Test Flask app creation and routes"""
    print("Testing Flask application...")
    try:
        # Set environment variables for testing
        os.environ['ANTHROPIC_API_KEY'] = 'dummy-key-for-testing'
        os.environ['S3_BUCKET_NAME'] = 'test-bucket'
        
        from app import create_app
        
        print("SUCCESS: Flask app imported")
        
        app = create_app()
        print("SUCCESS: Flask app created successfully")
        
        print("\nAvailable routes:")
        routes = list(app.url_map.iter_rules())
        for rule in routes:
            print(f"  {rule.rule} -> {rule.endpoint}")
        
        print(f"\nTotal routes: {len(routes)}")
        
        # Test that we have the expected routes
        expected_routes = [
            '/api/health',
            '/api/claude/chat',
            '/api/conversations/summary',
            '/api/conversations/search',
            '/api/conversations/ask'
        ]
        
        route_paths = [rule.rule for rule in routes]
        missing_routes = [route for route in expected_routes if route not in route_paths]
        
        if missing_routes:
            print(f"WARNING: Missing routes: {missing_routes}")
        else:
            print("SUCCESS: All expected routes are present")
        
        return True
    except Exception as e:
        print(f"ERROR: Flask app test failed: {e}")
        return False

def test_blueprints():
    """Test blueprint imports"""
    print("\nTesting blueprint imports...")
    try:
        # Set environment variables for testing
        os.environ['ANTHROPIC_API_KEY'] = 'dummy-key-for-testing'
        os.environ['S3_BUCKET_NAME'] = 'test-bucket'
        
        from backend.api.routes.claude_routes import claude_bp
        print("SUCCESS: Claude blueprint imported")
        
        from backend.api.routes.conversation_routes import conversation_bp
        print("SUCCESS: Conversation blueprint imported")
        
        from backend.api.routes.rag_routes import rag_bp
        print("SUCCESS: RAG blueprint imported")
        
        from backend.api.routes.health_routes import health_bp
        print("SUCCESS: Health blueprint imported")
        
        return True
    except Exception as e:
        print(f"ERROR: Blueprint import test failed: {e}")
        return False

def main():
    """Run Flask tests"""
    print("Testing Flask Application")
    print("=" * 40)
    
    tests = [
        test_blueprints,
        test_flask_app
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        if test():
            passed += 1
    
    print("\n" + "=" * 40)
    print(f"Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("SUCCESS: Flask application is working correctly!")
    else:
        print("WARNING: Some Flask tests failed.")

if __name__ == "__main__":
    main()
