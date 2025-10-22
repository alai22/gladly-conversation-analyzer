#!/usr/bin/env python3
"""
Test script for the web-based download system

This script tests the API endpoints to ensure they work correctly.
"""

import requests
import json
import time

def test_download_api():
    """Test the download API endpoints"""
    base_url = "http://localhost:5000"
    
    print("Testing Download API Endpoints...")
    print("=" * 50)
    
    # Test 1: Get download stats
    print("1. Testing GET /api/download/stats")
    try:
        response = requests.get(f"{base_url}/api/download/stats")
        if response.status_code == 200:
            data = response.json()
            print(f"   ✅ Success: {data['data']['total_downloaded']} conversations downloaded")
            print(f"   ✅ Total in CSV: {data['data']['total_in_csv']}")
            print(f"   ✅ Completion: {data['data']['completion_percentage']:.1f}%")
        else:
            print(f"   ❌ Error: {response.status_code} - {response.text}")
    except Exception as e:
        print(f"   ❌ Exception: {e}")
    
    print()
    
    # Test 2: Get download status
    print("2. Testing GET /api/download/status")
    try:
        response = requests.get(f"{base_url}/api/download/status")
        if response.status_code == 200:
            data = response.json()
            print(f"   ✅ Success: Download running = {data['data']['is_running']}")
            print(f"   ✅ Progress: {data['data']['progress_percentage']:.1f}%")
        else:
            print(f"   ❌ Error: {response.status_code} - {response.text}")
    except Exception as e:
        print(f"   ❌ Exception: {e}")
    
    print()
    
    # Test 3: Get download history
    print("3. Testing GET /api/download/history")
    try:
        response = requests.get(f"{base_url}/api/download/history")
        if response.status_code == 200:
            data = response.json()
            print(f"   ✅ Success: {len(data['data']['files'])} files found")
            for file in data['data']['files'][:3]:  # Show first 3 files
                print(f"   📁 {file['filename']}: {file['conversation_count']} conversations, {file['size_mb']:.1f} MB")
        else:
            print(f"   ❌ Error: {response.status_code} - {response.text}")
    except Exception as e:
        print(f"   ❌ Exception: {e}")
    
    print()
    
    # Test 4: Start a small test download
    print("4. Testing POST /api/download/start (small batch)")
    try:
        response = requests.post(
            f"{base_url}/api/download/start",
            json={
                "batch_size": 10,
                "max_duration_minutes": 2
            }
        )
        if response.status_code == 200:
            data = response.json()
            print(f"   ✅ Success: {data['message']}")
            
            # Wait a bit and check status
            print("   ⏳ Waiting 5 seconds...")
            time.sleep(5)
            
            status_response = requests.get(f"{base_url}/api/download/status")
            if status_response.status_code == 200:
                status_data = status_response.json()
                print(f"   📊 Status: Running = {status_data['data']['is_running']}")
                print(f"   📊 Progress: {status_data['data']['progress_percentage']:.1f}%")
                print(f"   📊 Downloaded: {status_data['data']['downloaded_count']}")
            
        else:
            print(f"   ❌ Error: {response.status_code} - {response.text}")
    except Exception as e:
        print(f"   ❌ Exception: {e}")
    
    print()
    print("=" * 50)
    print("API Test Complete!")
    print()
    print("To test the full web interface:")
    print("1. Start the Flask app: python app.py")
    print("2. Open browser: http://localhost:5000")
    print("3. Navigate to 'Download Manager' mode")
    print("4. Use the web interface to start downloads")

if __name__ == "__main__":
    test_download_api()
