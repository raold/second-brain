# Google OAuth Setup for Second Brain v4.2.3

## Quick Setup Guide

### Step 1: Get Google Cloud Credentials

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select existing one
3. Enable **Google Drive API**:
   - Go to "APIs & Services" → "Library"
   - Search for "Google Drive API"
   - Click "Enable"

4. Create OAuth 2.0 Credentials:
   - Go to "APIs & Services" → "Credentials"
   - Click "Create Credentials" → "OAuth 2.0 Client ID"
   - Configure OAuth consent screen if prompted:
     - Choose "External" for personal use
     - Fill in required fields
     - Add test users (your email)
   - Application type: **Web application**
   - Name: "Second Brain Google Drive"
   - Authorized redirect URIs:
     ```
     http://localhost:8001/gdrive/callback
     http://localhost:8001/api/v1/gdrive/callback
     ```
   - Click "Create"

5. Download credentials:
   - Click the download button next to your OAuth 2.0 Client
   - Save as `credentials.json`

### Step 2: Configure Second Brain

Create or update `.env` file:
```bash
# Google OAuth Configuration
GOOGLE_CLIENT_ID=your-client-id.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=your-client-secret
GOOGLE_REDIRECT_URI=http://localhost:8001/api/v1/gdrive/callback

# PostgreSQL (for production use)
DATABASE_URL=postgresql://user:password@localhost/secondbrain
# Or use mock for testing
USE_MOCK_DATABASE=true

# OpenAI (optional, for AI features)
OPENAI_API_KEY=sk-... # or 'mock' for testing
```

### Step 3: Start the Application

```bash
# Start with Google Drive integration
./start_with_gdrive.sh

# Or manually:
source venv/bin/activate
export $(cat .env | xargs)
uvicorn app.main:app --reload --port 8001
```

### Step 4: Connect Google Drive

1. Open http://localhost:8001/static/gdrive-ui.html
2. Click "Connect Google Drive"
3. Authorize access in Google's OAuth screen
4. You'll be redirected back to Second Brain
5. Start syncing your files!

## Environment Variables

| Variable | Description | Example |
|----------|-------------|---------|
| GOOGLE_CLIENT_ID | OAuth 2.0 Client ID | 123456789.apps.googleusercontent.com |
| GOOGLE_CLIENT_SECRET | OAuth 2.0 Client Secret | GOCSPX-xxxxxxxxxxxx |
| GOOGLE_REDIRECT_URI | OAuth callback URL | http://localhost:8001/api/v1/gdrive/callback |
| DATABASE_URL | PostgreSQL connection | postgresql://user:pass@localhost/db |
| USE_MOCK_DATABASE | Use mock DB for testing | true/false |

## Troubleshooting

### "Google credentials not configured"
- Make sure GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET are set in .env
- Restart the application after setting environment variables

### "Redirect URI mismatch"
- Ensure the redirect URI in Google Cloud Console matches exactly:
  `http://localhost:8001/api/v1/gdrive/callback`
- Don't forget to save changes in Google Cloud Console

### "Access blocked" error
- Make sure you've configured the OAuth consent screen
- Add your email as a test user if the app is in testing mode

### Port 8001 already in use
```bash
lsof -ti:8001 | xargs kill -9
```

## Security Notes

- Never commit `.env` file to git
- Keep your client secret secure
- In production, use HTTPS for redirect URIs
- Rotate credentials periodically

## Next Steps

After setup:
1. Files from Google Drive will be converted to memories in PostgreSQL
2. Use the search features to find content across all synced files
3. The AI will help you discover connections between documents
4. All data stays in your PostgreSQL database - Google Drive is only read