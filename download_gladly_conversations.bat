@echo off
echo Gladly Conversation Downloader
echo =============================
echo.

REM Check if GLADLY_API_KEY is set
if "%GLADLY_API_KEY%"=="" (
    echo ERROR: GLADLY_API_KEY environment variable is not set
    echo.
    echo Please set your Gladly API key first:
    echo set GLADLY_API_KEY=your-gladly-api-key-here
    echo.
    pause
    exit /b 1
)

echo API key is set. Starting download process...
echo.

REM Test the API connection first
echo Step 1: Testing API connection...
python test_gladly_downloader.py

if %ERRORLEVEL% neq 0 (
    echo.
    echo ERROR: API test failed. Please check your API key and try again.
    pause
    exit /b 1
)

echo.
echo Step 2: API test successful! Starting full download...
echo This may take a while depending on the number of conversations...
echo.

REM Run the main downloader
python gladly_downloader.py

echo.
echo Download process completed!
echo Check gladly_download.log for detailed information.
echo.
pause
