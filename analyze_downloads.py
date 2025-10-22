#!/usr/bin/env python3
"""
Gladly Conversation Analyzer

This script analyzes downloaded conversations and provides statistics
to help you decide how many more conversations to download.
"""

import json
import os
import csv
from typing import Dict, List, Set
from datetime import datetime
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ConversationAnalyzer:
    """Analyzes downloaded conversation data"""
    
    def __init__(self):
        self.downloaded_conversations = set()
        self.total_conversations_in_csv = 0
        self.conversation_stats = {}
        
    def analyze_downloaded_files(self) -> Dict:
        """Analyze all downloaded conversation files"""
        logger.info("Analyzing downloaded conversation files...")
        
        # Look for all downloaded files
        downloaded_files = []
        for file in os.listdir('.'):
            if file.startswith('gladly_conversations') and file.endswith('.jsonl'):
                downloaded_files.append(file)
        
        if not downloaded_files:
            logger.warning("No downloaded conversation files found")
            return self._get_summary()
        
        logger.info(f"Found {len(downloaded_files)} downloaded files:")
        for file in downloaded_files:
            logger.info(f"  - {file}")
        
        # Analyze each file
        total_items = 0
        total_conversations = 0
        
        for file in downloaded_files:
            logger.info(f"\nAnalyzing {file}...")
            file_stats = self._analyze_file(file)
            total_items += file_stats['total_items']
            total_conversations += file_stats['total_conversations']
            
            # Add to downloaded conversations set
            self.downloaded_conversations.update(file_stats['conversation_ids'])
        
        logger.info(f"\nTotal downloaded conversations: {total_conversations}")
        logger.info(f"Total conversation items: {total_items}")
        
        return self._get_summary()
    
    def _analyze_file(self, filename: str) -> Dict:
        """Analyze a single downloaded file"""
        stats = {
            'filename': filename,
            'total_conversations': 0,
            'total_items': 0,
            'conversation_ids': set(),
            'file_size_mb': 0,
            'date_range': {'earliest': None, 'latest': None}
        }
        
        try:
            file_size = os.path.getsize(filename)
            stats['file_size_mb'] = round(file_size / (1024 * 1024), 2)
            
            with open(filename, 'r', encoding='utf-8') as f:
                for line_num, line in enumerate(f, 1):
                    if line.strip():
                        try:
                            data = json.loads(line)
                            
                            # Count conversations
                            if '_metadata' in data and 'conversation_id' in data['_metadata']:
                                conv_id = data['_metadata']['conversation_id']
                                stats['conversation_ids'].add(conv_id)
                                stats['total_conversations'] += 1
                            
                            # Count items
                            if 'items' in data and isinstance(data['items'], list):
                                stats['total_items'] += len(data['items'])
                            
                            # Track date range
                            if '_metadata' in data and 'downloaded_at' in data['_metadata']:
                                download_time = data['_metadata']['downloaded_at']
                                if not stats['date_range']['earliest'] or download_time < stats['date_range']['earliest']:
                                    stats['date_range']['earliest'] = download_time
                                if not stats['date_range']['latest'] or download_time > stats['date_range']['latest']:
                                    stats['date_range']['latest'] = download_time
                                    
                        except json.JSONDecodeError as e:
                            logger.warning(f"JSON decode error in {filename} line {line_num}: {e}")
                            
        except Exception as e:
            logger.error(f"Error analyzing {filename}: {e}")
        
        logger.info(f"  File size: {stats['file_size_mb']} MB")
        logger.info(f"  Conversations: {stats['total_conversations']}")
        logger.info(f"  Items: {stats['total_items']}")
        if stats['date_range']['earliest']:
            logger.info(f"  Date range: {stats['date_range']['earliest']} to {stats['date_range']['latest']}")
        
        return stats
    
    def analyze_csv_file(self, csv_file: str = "data/conversation_metrics.csv") -> int:
        """Analyze the CSV file to get total conversation count"""
        logger.info(f"\nAnalyzing CSV file: {csv_file}")
        
        if not os.path.exists(csv_file):
            logger.error(f"CSV file not found: {csv_file}")
            return 0
        
        total_conversations = 0
        csv_conversation_ids = set()
        
        try:
            with open(csv_file, 'r', encoding='utf-8') as file:
                reader = csv.DictReader(file)
                for row in reader:
                    conversation_id = row.get('Conversation ID', '').strip()
                    if conversation_id and conversation_id != '':
                        csv_conversation_ids.add(conversation_id)
                        total_conversations += 1
            
            self.total_conversations_in_csv = total_conversations
            logger.info(f"Total conversations in CSV: {total_conversations}")
            
            # Check overlap with downloaded conversations
            downloaded_set = self.downloaded_conversations
            overlap = len(downloaded_set.intersection(csv_conversation_ids))
            logger.info(f"Downloaded conversations that match CSV: {overlap}")
            
            return total_conversations
            
        except Exception as e:
            logger.error(f"Error analyzing CSV file: {e}")
            return 0
    
    def _get_summary(self) -> Dict:
        """Get summary statistics"""
        return {
            'downloaded_conversations': len(self.downloaded_conversations),
            'total_in_csv': self.total_conversations_in_csv,
            'remaining_to_download': max(0, self.total_conversations_in_csv - len(self.downloaded_conversations)),
            'completion_percentage': (len(self.downloaded_conversations) / self.total_conversations_in_csv * 100) if self.total_conversations_in_csv > 0 else 0
        }
    
    def get_download_recommendations(self) -> Dict:
        """Get recommendations for next download batch"""
        summary = self._get_summary()
        
        recommendations = {
            'small_batch': 100,      # ~2-3 minutes
            'medium_batch': 500,     # ~10-15 minutes  
            'large_batch': 1000,    # ~20-30 minutes
            'estimated_time_per_conversation': 0.15  # seconds
        }
        
        # Calculate estimated times
        for batch_type in ['small_batch', 'medium_batch', 'large_batch']:
            count = recommendations[batch_type]
            estimated_minutes = (count * recommendations['estimated_time_per_conversation']) / 60
            recommendations[f'{batch_type}_minutes'] = round(estimated_minutes, 1)
        
        return recommendations

def main():
    """Main function"""
    analyzer = ConversationAnalyzer()
    
    print("=" * 60)
    print("GLADLY CONVERSATION DOWNLOAD ANALYSIS")
    print("=" * 60)
    
    # Analyze downloaded files
    analyzer.analyze_downloaded_files()
    
    # Analyze CSV file
    total_in_csv = analyzer.analyze_csv_file()
    
    # Get final summary after both analyses
    summary = analyzer._get_summary()
    recommendations = analyzer.get_download_recommendations()
    
    # Display summary
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print(f"Total conversations in CSV: {summary['total_in_csv']:,}")
    print(f"Already downloaded: {summary['downloaded_conversations']:,}")
    print(f"Remaining to download: {summary['remaining_to_download']:,}")
    print(f"Completion: {summary['completion_percentage']:.1f}%")
    
    print("\n" + "=" * 60)
    print("DOWNLOAD RECOMMENDATIONS")
    print("=" * 60)
    print(f"Small batch (100 conversations): ~{recommendations['small_batch_minutes']} minutes")
    print(f"Medium batch (500 conversations): ~{recommendations['medium_batch_minutes']} minutes")
    print(f"Large batch (1000 conversations): ~{recommendations['large_batch_minutes']} minutes")
    
    print("\n" + "=" * 60)
    print("NEXT STEPS")
    print("=" * 60)
    print("1. Decide how many conversations you want to download next")
    print("2. Run: python gladly_batch_downloader.py")
    print("3. Or modify the batch size in the script")
    
    if summary['remaining_to_download'] > 0:
        print(f"\nSuggested next batch size: {min(500, summary['remaining_to_download'])} conversations")

if __name__ == "__main__":
    main()
