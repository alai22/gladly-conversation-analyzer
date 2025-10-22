#!/usr/bin/env python3
"""
Test script for the new modular architecture
"""

def test_imports():
    """Test all imports"""
    print("Testing imports...")
    try:
        from backend.utils.config import Config
        print("SUCCESS: Config imported")
        
        from backend.utils.logging import setup_logging
        print("SUCCESS: Logging imported")
        
        from backend.models.conversation import ConversationItem, ConversationSummary
        print("SUCCESS: Models imported")
        
        from backend.utils.helpers import truncate_text, extract_json_from_text
        print("SUCCESS: Helpers imported")
        
        return True
    except Exception as e:
        print(f"ERROR: Import failed: {e}")
        return False

def test_configuration():
    """Test configuration"""
    print("\nTesting configuration...")
    try:
        from backend.utils.config import Config
        
        print(f"Storage Type: {Config.STORAGE_TYPE}")
        print(f"Flask Debug: {Config.FLASK_DEBUG}")
        print(f"Port: {Config.PORT}")
        print(f"Host: {Config.HOST}")
        
        print("SUCCESS: Configuration loaded successfully")
        return True
    except Exception as e:
        print(f"ERROR: Configuration test failed: {e}")
        return False

def test_data_models():
    """Test data models"""
    print("\nTesting data models...")
    try:
        from backend.models.conversation import ConversationItem, ConversationSummary
        
        # Test ConversationItem
        item_data = {
            'id': 'test123',
            'timestamp': '2024-01-01T10:00:00Z',
            'customerId': 'cust1',
            'conversationId': 'conv1',
            'content': {
                'type': 'CHAT_MESSAGE',
                'content': 'Hello world',
                'messageType': 'CUSTOMER'
            }
        }
        
        item = ConversationItem.from_dict(item_data)
        print(f"SUCCESS: ConversationItem created: {item.content_type}")
        print(f"   Searchable text: {item.searchable_text[:50]}...")
        
        # Test ConversationSummary
        summary = ConversationSummary(
            total_items=1,
            unique_customers=1,
            unique_conversations=1,
            date_range={'start': '2024-01-01', 'end': '2024-01-01'},
            content_types={'CHAT_MESSAGE': 1},
            message_types={'CUSTOMER': 1}
        )
        
        print("SUCCESS: ConversationSummary created")
        print(f"   Summary string length: {len(summary.to_string())}")
        
        return True
    except Exception as e:
        print(f"ERROR: Data models test failed: {e}")
        return False

def test_utility_functions():
    """Test utility functions"""
    print("\nTesting utility functions...")
    try:
        from backend.utils.helpers import truncate_text, extract_json_from_text
        
        # Test truncate_text
        long_text = "This is a very long text that should be truncated when it exceeds the maximum length"
        truncated = truncate_text(long_text, 30)
        print(f"SUCCESS: Truncate: '{truncated}'")
        
        # Test extract_json_from_text
        text_with_json = 'Here is some text {"key": "value", "number": 123} more text'
        json_data = extract_json_from_text(text_with_json)
        print(f"SUCCESS: JSON extraction: {json_data}")
        
        return True
    except Exception as e:
        print(f"ERROR: Utility functions test failed: {e}")
        return False

def test_logging():
    """Test logging setup"""
    print("\nTesting logging...")
    try:
        from backend.utils.logging import setup_logging, get_logger
        
        logger = setup_logging(level='INFO')
        test_logger = get_logger('test')
        
        test_logger.info("Test log message")
        print("SUCCESS: Logging setup successful")
        
        return True
    except Exception as e:
        print(f"ERROR: Logging test failed: {e}")
        return False

def main():
    """Run all tests"""
    print("Testing New Modular Architecture")
    print("=" * 50)
    
    tests = [
        test_imports,
        test_configuration,
        test_data_models,
        test_utility_functions,
        test_logging
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        if test():
            passed += 1
    
    print("\n" + "=" * 50)
    print(f"Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("SUCCESS: All tests passed! The modular architecture is working correctly.")
    else:
        print("WARNING: Some tests failed. Check the errors above.")
    
    return passed == total

if __name__ == "__main__":
    main()
