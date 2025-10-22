# Data Directory

This directory contains data files used by the Gladly Conversation Analyzer.

## Files

### `conversation_metrics.csv`
- **Purpose**: Index file containing conversation metadata from Gladly
- **Format**: CSV with columns: Timestamp Created At Date, Conversation ID, Last Channel, Assigned Agent Name, Topics, Conversation Link
- **Usage**: Used by the download manager to:
  - Get list of conversation IDs to download
  - Filter conversations by date range
  - Track download progress
- **Size**: ~73,000 conversations
- **Update Frequency**: Should be updated periodically with latest conversation data from Gladly

## Security Note

This CSV file contains conversation metadata but not the actual conversation content. It's safe to include in version control as it serves as an index for downloading the actual conversation data via the Gladly API.

## Usage

The download manager uses this file to:
1. Parse conversation IDs and timestamps
2. Filter conversations by date range
3. Track which conversations have been downloaded
4. Provide progress statistics

## Updating the Data

To update this file with latest conversation data:
1. Export conversation metrics from Gladly admin panel
2. Replace this file with the new export
3. Commit and push to deploy the updated index
