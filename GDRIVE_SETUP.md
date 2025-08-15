# Google Drive Integration Setup Guide

## What You Need

For Google Drive integration to work, you need **Google Cloud Platform credentials**:

### Option 1: Quick Demo Mode (No Google Account Needed)
Just run the demo to see the UI:
```bash
python3 start_gdrive_demo.py
```
This shows the interface but doesn't connect to real Google Drive.

### Option 2: Full Google Drive Integration

1. **Get Google Cloud Credentials:**
   - Go to https://console.cloud.google.com/
   - Create a new project or select existing
   - Enable "Google Drive API"
   - Go to "Credentials" → "Create Credentials" → "OAuth 2.0 Client ID"
   - Application type: "Web application"
   - Add authorized redirect URI: `http://localhost:8001/gdrive/callback`
   - Download the credentials JSON

2. **Set up credentials:**
   ```bash
   # Create credentials directory
   mkdir -p credentials
   
   # Save your Google credentials
   # Copy the downloaded JSON to:
   credentials/google_client_secrets.json
   ```

3. **Update .env file:**
   ```bash
   # Google Drive Settings
   GOOGLE_CLIENT_ID=your-client-id.apps.googleusercontent.com
   GOOGLE_CLIENT_SECRET=your-client-secret
   GOOGLE_REDIRECT_URI=http://localhost:8001/gdrive/callback
   
   # OpenAI (optional - for AI features)
   OPENAI_API_KEY=sk-... (or use 'mock' for testing)
   ```

## Running the Application

### Simple Demo (No Setup Required):
```bash
# Just see the UI
python3 start_gdrive_demo.py
```

### Full Application (Requires Google Credentials):
```bash
# With real Google Drive connection
./run_gdrive_branch.sh
```

## Accessing the Interface

Once running, open your browser to:
- **Main UI**: http://localhost:8001/static/gdrive-ui.html
- **API Status**: http://localhost:8001/api/gdrive/status
- **Documentation**: http://localhost:8001/static/api-documentation.html

## Troubleshooting

### "No module named X" errors:
The feature/gdrive branch has dependency conflicts with Python 3.13. Use the demo mode instead.

### "API key required" prompts:
- For Google Drive: You need Google Cloud credentials (see above)
- For OpenAI: Use 'mock' for testing or get a key from https://platform.openai.com

### Port 8001 already in use:
```bash
# Kill existing processes
pkill -f "8001"
lsof -ti:8001 | xargs kill -9
```

### Can't connect to Google Drive:
Make sure you have:
1. Created OAuth 2.0 credentials in Google Cloud Console
2. Enabled Google Drive API
3. Added http://localhost:8001/gdrive/callback as redirect URI
4. Saved credentials to credentials/google_client_secrets.json

## Current Status

✅ **What's Working:**
- Complete UI interface (HTML/CSS/JS)
- OAuth flow implementation
- File streaming architecture
- API endpoints defined
- Documentation available

⚠️ **Known Issues:**
- Python 3.13 compatibility issues with some dependencies
- Full app requires many dependencies that may conflict
- Demo mode is recommended for testing the UI

## Quick Test

To quickly see if everything is working:
```bash
# Start demo server
python3 start_gdrive_demo.py

# In another terminal, test the API
curl http://localhost:8001/api/gdrive/status
```

You should see a JSON response indicating demo mode is active.