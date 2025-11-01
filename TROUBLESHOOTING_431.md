# Troubleshooting HTTP 431 Error

## Quick Fix Steps

### 1. **Stop All Running Servers**
```bash
# Press Ctrl+C in the terminal where npm run dev is running
# Or kill the processes:
# Windows PowerShell:
Get-Process python | Where-Object {$_.Path -like "*gladly*"} | Stop-Process -Force
Get-Process node | Where-Object {$_.Path -like "*react-scripts*"} | Stop-Process -Force
```

### 2. **Restart the Development Environment**
```bash
npm run dev
```

### 3. **Verify the Fix is Applied**
Look for this line in the Flask server console output:
```
Max header size: 32768 bytes
```

If you see `8192 bytes` or don't see this line, the fix isn't applied.

## What Was Fixed

The HTTP 431 "Request Header Fields Too Large" error occurs when request headers exceed Flask/Werkzeug's default limit of 8KB.

**Fix Applied:**
- Increased `max_header_size` from 8192 bytes (8KB) to 32768 bytes (32KB)
- Applied in both `app.py` and `serve.py`
- Must be set BEFORE Flask imports (done at top of files)

## Why It Happens

Large headers can be caused by:
- Browser storing large cookies
- Development tools adding extra headers
- React DevTools or browser extensions
- Multiple/large custom headers

## If the Error Persists

1. **Clear Browser Cookies:**
   - Open Developer Tools (F12)
   - Application tab → Cookies
   - Delete all cookies for `localhost:5000` and `localhost:3000`

2. **Check Request Logs:**
   - Look at Flask console output
   - Should see: `[REQUEST] ... Header Size: XXXX bytes`
   - If Header Size > 8000, that's the problem

3. **Try Incognito/Private Mode:**
   - This will eliminate cookie issues
   - If it works in incognito, cookies are the problem

4. **Check React Dev Server Proxy:**
   - The proxy in `package.json` forwards requests
   - Make sure Flask server is running on port 5000

## Manual Server Restart

If `npm run dev` isn't working:

**Terminal 1 (Backend):**
```bash
# Windows:
python app.py

# Linux/Mac:
source venv/bin/activate && python app.py
```

**Terminal 2 (Frontend):**
```bash
npm start
```

## Still Having Issues?

1. Check Flask console logs for header sizes
2. Try accessing Flask directly: `http://localhost:5000/api/health`
3. Verify `werkzeug.serving.WSGIRequestHandler.max_header_size = 32768` is at the top of `app.py`

