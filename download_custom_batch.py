#!/usr/bin/env python3
"""
Custom Gladly Conversation Downloader

This script allows you to specify exactly how many conversations to download.
"""

import sys
import os
from dotenv import load_dotenv
from gladly_batch_downloader import BatchedGladlyDownloader

# Load environment variables
load_dotenv()

def main():
    """Main function with user input for batch size"""
    
    # Get API credentials
    api_key = os.getenv('GLADLY_API_KEY')
    agent_email = os.getenv('GLADLY_AGENT_EMAIL')
    
    if not api_key or not agent_email:
        print("ERROR: Please set GLADLY_API_KEY and GLADLY_AGENT_EMAIL in your .env file")
        return
    
    # Get batch size from user
    if len(sys.argv) > 1:
        try:
            batch_size = int(sys.argv[1])
        except ValueError:
            print("ERROR: Please provide a valid number for batch size")
            return
    else:
        try:
            batch_size = int(input("How many conversations do you want to download? (default: 500): ") or "500")
        except ValueError:
            print("ERROR: Please provide a valid number")
            return
    
    if batch_size <= 0:
        print("ERROR: Batch size must be greater than 0")
        return
    
    # Calculate estimated time
    estimated_minutes = (batch_size * 0.15) / 60
    
    print(f"\nStarting download of {batch_size} conversations...")
    print(f"Estimated time: ~{estimated_minutes:.1f} minutes")
    print("Press Ctrl+C to stop early if needed\n")
    
    # Initialize downloader
    downloader = BatchedGladlyDownloader(api_key, agent_email)
    
    # Download with custom batch size
    downloader.download_batch(
        csv_file="Conversation Metrics (ID, Topic, Channel, Agent).csv",
        output_file="gladly_conversations_batch.jsonl",
        max_duration_minutes=60,  # Large time limit, we'll stop by count
        batch_size=batch_size
    )

if __name__ == "__main__":
    main()
