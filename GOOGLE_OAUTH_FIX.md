# Fixing Google OAuth "Access Blocked" Error

## The Problem
Google blocks OAuth requests that don't meet their security requirements. For development with `localhost`, you need to configure your OAuth app properly.

## Solution Steps

### 1. Configure OAuth Consent Screen
1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Select your project (or create a new one)
3. Navigate to **APIs & Services** → **OAuth consent screen**
4. Configure as follows:
   - **User Type**: External (but keep in testing mode)
   - **App name**: Second Brain Dev
   - **User support email**: dro@lynchburgsmiles.com
   - **Developer contact**: dro@lynchburgsmiles.com

### 2. Add Test Users (REQUIRED)
While in the OAuth consent screen:
1. Scroll to **Test users** section
2. Click **+ ADD USERS**
3. Add: `dro@lynchburgsmiles.com`
4. Click **SAVE**

### 3. Verify Redirect URIs
1. Go to **APIs & Services** → **Credentials**
2. Click on your OAuth 2.0 Client ID
3. Under **Authorized redirect URIs**, ensure you have:
   - `http://localhost:8001/api/v1/gdrive/callback`
   - `http://127.0.0.1:8001/api/v1/gdrive/callback` (as backup)
4. Click **SAVE**

### 4. Enable Required APIs
1. Go to **APIs & Services** → **Library**
2. Search and enable:
   - Google Drive API
   - Google+ API (for user info)
3. Wait 5 minutes for changes to propagate

## Alternative: Use Service Account (No OAuth Flow)

If OAuth continues to fail, use a service account instead:

```python
# Create service account credentials
from google.oauth2 import service_account

credentials = service_account.Credentials.from_service_account_file(
    'path/to/service-account-key.json',
    scopes=['https://www.googleapis.com/auth/drive.readonly']
)
```

## Testing the Fix

After adding yourself as a test user:

```bash
# Restart the app
wsl bash -c "cd /mnt/c/Users/dro/second-brain && source .env && python3 -m uvicorn app.main:app --port 8001 --reload"

# Try authentication again
open http://localhost:8001/static/gdrive-ui.html
```

## Common Issues

### "App is in testing mode"
This is GOOD for development. It means only test users can authenticate.

### "Redirect URI mismatch"
Ensure the URI in your .env EXACTLY matches what's in Google Console:
- Include the protocol (http://)
- Include the port (:8001)
- Include the full path (/api/v1/gdrive/callback)

### "Invalid client"
Your client secret might have expired. Generate a new one:
1. Go to Credentials
2. Click on your OAuth client
3. Click "RESET SECRET"
4. Update .env with new secret

## Quick Checklist

- [ ] OAuth consent screen configured
- [ ] App in "Testing" mode
- [ ] Test user added (dro@lynchburgsmiles.com)
- [ ] Redirect URIs match exactly
- [ ] Google Drive API enabled
- [ ] Client ID and Secret are current
- [ ] .env file has correct values

Once you've added yourself as a test user, the authentication should work!