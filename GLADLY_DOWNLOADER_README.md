# Gladly Conversation Downloader

This script downloads conversation items from the Gladly API using conversation IDs from the CSV file.

## Setup

1. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Set up environment variables:**
   ```bash
   # Copy the example environment file
   cp env.example .env
   
   # Edit .env and add your Gladly API key
   GLADLY_API_KEY=your-gladly-api-key-here
   ```

3. **Set the API key in your environment:**
   ```bash
   # Windows PowerShell
   $env:GLADLY_API_KEY="your-gladly-api-key-here"
   
   # Linux/Mac
   export GLADLY_API_KEY="your-gladly-api-key-here"
   ```

## Usage

### Test the API connection first:
```bash
python test_gladly_downloader.py
```

This will test the downloader with a few conversation IDs to verify the API connection works.

### Download all conversations:
```bash
python gladly_downloader.py
```

This will:
- Read all conversation IDs from `Conversation Metrics (ID, Topic, Channel, Agent).csv`
- Download conversation items for each ID using the Gladly API
- Save all data to a timestamped JSONL file (e.g., `gladly_conversations_20241201_143022.jsonl`)
- Log progress and any errors to `gladly_download.log`

## Output

The script creates:
- **JSONL file**: Contains all downloaded conversation data in JSON Lines format
- **Log file**: `gladly_download.log` with detailed progress and error information
- **Test results**: `test_results.json` (when running the test script)

## Configuration

You can modify the download behavior by editing the parameters in `gladly_downloader.py`:

- `batch_size`: How often to log progress (default: 50)
- `delay`: Delay between API requests in seconds (default: 0.1)
- `output_file`: Custom output filename (default: auto-generated with timestamp)

## Error Handling

The script handles:
- Network timeouts and connection errors
- API rate limiting (with configurable delays)
- Missing or invalid conversation IDs
- Authentication errors
- Server errors (404, 500, etc.)

Failed downloads are logged but don't stop the overall process.
