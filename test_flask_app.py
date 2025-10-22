#!/usr/bin/env python3
"""
Test script for Flask application
"""

def test_flask_app():
    """Test Flask app creation and routes"""
    print("Testing Flask application...")
    try:
        from app import create_app
        
        print("SUCCESS: Flask app imported")
        
        app = create_app()
        print("SUCCESS: Flask app created successfully")
        
        print("\nAvailable routes:")
        for rule in app.url_map.iter_rules():
            print(f"  {rule.rule} -> {rule.endpoint}")
        
        print(f"\nTotal routes: {len(list(app.url_map.iter_rules()))}")
        
        return True
    except Exception as e:
        print(f"ERROR: Flask app test failed: {e}")
        return False

def test_blueprints():
    """Test blueprint imports"""
    print("\nTesting blueprint imports...")
    try:
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
