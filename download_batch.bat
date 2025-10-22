@echo off
echo Gladly Batch Conversation Downloader
echo ====================================
echo.

REM Check if GLADLY_API_KEY and GLADLY_AGENT_EMAIL are set
if "%GLADLY_API_KEY%"=="" (
    echo ERROR: GLADLY_API_KEY environment variable is not set
    echo.
    echo Please set your Gladly API key first:
    echo set GLADLY_API_KEY=your-gladly-api-key-here
    echo.
    pause
    exit /b 1
)

if "%GLADLY_AGENT_EMAIL%"=="" (
    echo ERROR: GLADLY_AGENT_EMAIL environment variable is not set
    echo.
    echo Please set your agent email first:
    echo set GLADLY_AGENT_EMAIL=your.email@halocollar.com
    echo.
    pause
    exit /b 1
)

echo API credentials are set. Starting 5-minute batch download...
echo This will download conversations and save progress for resuming later.
echo.

REM Run the batched downloader
python gladly_batch_downloader.py

echo.
echo Batch download completed!
echo Check gladly_batch_download.log for detailed information.
echo.
echo To run another batch, simply run this script again.
echo.
pause
