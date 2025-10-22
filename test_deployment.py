#!/usr/bin/env python3
"""
Test script to verify deployment configuration
"""

import os
import sys
import traceback

def test_imports():
    """Test if all modules can be imported"""
    print("Testing module imports...")
    
    try:
        # Test backend imports
        from backend.utils.config import Config
        print("✅ Backend config imported successfully")
        
        from backend.services.claude_service import ClaudeService
        print("✅ Claude service imported successfully")
        
        from backend.services.conversation_service import ConversationService
        print("✅ Conversation service imported successfully")
        
        # Test main app
        from app import app
        print("✅ Main app imported successfully")
        
        return True
        
    except Exception as e:
        print(f"❌ Import failed: {e}")
        traceback.print_exc()
        return False

def test_config():
    """Test configuration"""
    print("\nTesting configuration...")
    
    try:
        from backend.utils.config import Config
        
        print(f"Storage type: {Config.STORAGE_TYPE}")
        print(f"S3 bucket: {Config.S3_BUCKET_NAME}")
        print(f"API key set: {'Yes' if Config.ANTHROPIC_API_KEY else 'No'}")
        print(f"Host: {Config.HOST}")
        print(f"Port: {Config.PORT}")
        
        # Validate config
        is_valid = Config.validate()
        print(f"Config valid: {'Yes' if is_valid else 'No'}")
        
        return is_valid
        
    except Exception as e:
        print(f"❌ Config test failed: {e}")
        return False

def test_environment():
    """Test environment variables"""
    print("\nTesting environment variables...")
    
    env_vars = [
        'ANTHROPIC_API_KEY',
        'S3_BUCKET_NAME', 
        'AWS_ACCESS_KEY_ID',
        'AWS_SECRET_ACCESS_KEY',
        'STORAGE_TYPE',
        'PORT',
        'HOST'
    ]
    
    for var in env_vars:
        value = os.getenv(var)
        if value:
            # Mask sensitive values
            if 'KEY' in var or 'SECRET' in var:
                masked_value = value[:4] + '*' * (len(value) - 8) + value[-4:] if len(value) > 8 else '***'
                print(f"✅ {var}: {masked_value}")
            else:
                print(f"✅ {var}: {value}")
        else:
            print(f"❌ {var}: Not set")

def main():
    """Run all tests"""
    print("🔍 Gladly Deployment Test")
    print("=" * 50)
    
    # Test environment
    test_environment()
    
    # Test imports
    imports_ok = test_imports()
    
    # Test config
    config_ok = test_config()
    
    print("\n" + "=" * 50)
    if imports_ok and config_ok:
        print("✅ All tests passed! Deployment should work.")
    else:
        print("❌ Some tests failed. Check the errors above.")
        sys.exit(1)

if __name__ == "__main__":
    main()
