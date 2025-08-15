# Development Context - Second Brain v4.2.3

## Current State (August 15, 2025)

### ✅ What's Working
- **PostgreSQL Backend**: Production-ready with pgvector for embeddings
- **Google Drive Integration**: Full OAuth flow implemented and functional
  - User can authenticate with Google account
  - List and browse Google Drive files
  - Sync files to PostgreSQL as memories
  - Generate OpenAI embeddings (when API key configured)
- **Code Quality**: 10/10 linting score, PEP8 compliant, properly formatted
- **Tests**: All 28 tests passing locally and in CI
- **UI**: Beautiful Google Drive interface at `/static/gdrive-ui.html`

### 🔧 Current Implementation Details

#### Google OAuth Flow (Accurate as of Session 7)
1. **User Action**: Click "Connect Google Drive" in frontend
2. **Backend Request**: Frontend calls `/api/v1/gdrive/connect` endpoint
3. **Authorization URL Generation**: Backend constructs OAuth 2.0 URL with parameters
4. **Redirect to Google**: Frontend redirects browser to authorization URL
5. **User Consent**: User approves requested permissions (drive.readonly)
6. **Redirect to Callback**: Google redirects to `http://localhost:8001/api/v1/gdrive/callback`
7. **Code Exchange**: Callback exchanges authorization code for tokens
8. **Token Storage**: Currently stored IN MEMORY (problem - lost on restart)
9. **Confirmation**: User shown success page

#### Key Files
- `app/routes/gdrive_real.py`: FastAPI endpoints for OAuth flow
- `app/services/google_drive_simple.py`: Google Drive API business logic
- `docs/google-drive-integration.md`: User-facing setup guide

### ⚠️ Critical Issues

1. **Token Persistence**: Tokens stored in memory are lost on restart
   - User must re-authenticate every time server restarts
   - No refresh token logic implemented
   - Not suitable for production use

2. **Security Considerations**
   - Tokens should be encrypted before storage
   - Need secure local storage solution
   - Must not commit tokens to git

### 🎯 Next Steps (Priority Order)

1. **Implement Token Persistence**
   - Store tokens in `.gdrive_tokens.json` (local file)
   - Encrypt tokens using Fernet encryption
   - Add to `.gitignore` to prevent git commits
   
2. **Add Token Refresh Logic**
   - Check if access token expired before API calls
   - Use refresh token to get new access token
   - Update stored tokens automatically

3. **Improve User Experience**
   - Auto-reconnect on server restart if tokens exist
   - Show connection status in UI
   - Handle token expiration gracefully

## User Preferences & Context

### Development Style
- **Autonomous Mode**: No confirmations needed, execute immediately
- **Cross-Platform**: Works on Windows, macOS, Linux
- **No Co-Author Lines**: Don't add co-author lines to commits
- **Production Focus**: Real implementation, not demos

### Technical Constraints
- **Single User**: Designed for personal use
- **Docker Deployment**: Will run in Docker container
- **PostgreSQL Only**: No SQLite, Redis, or other databases
- **Local Storage OK**: Can use local files for single-user tokens

## Session History

### Session 7 (August 15, 2025)
- Implemented real Google Drive integration
- Fixed all linting and code quality issues
- Cleaned up repository (removed 17 temp files)
- Added proper dependencies to requirements.txt
- Tests passing in CI
- **Issue Identified**: Token persistence needed

### Previous Sessions
- Sessions 1-6: Built v4.2.3 with PostgreSQL backend
- Extensive testing and documentation cleanup
- Security patches applied
- Production-ready base system

## Architecture Decisions

### Token Storage Solution (Proposed)
```python
# Store in: .gdrive_tokens.json
{
    "access_token": "encrypted_token_here",
    "refresh_token": "encrypted_token_here",
    "token_expiry": "2025-08-15T12:00:00Z",
    "user_email": "dro@lynchburgsmiles.com"
}
```

### Security Implementation
- Use `cryptography.fernet` for symmetric encryption
- Derive key from `ENCRYPTION_KEY` in `.env`
- Never store plaintext tokens
- Validate token integrity on load

## Testing Status

### What's Tested
- Basic functionality (28 tests)
- Import verification
- Mock services
- Factory pattern

### What Needs Testing
- Token persistence
- Token refresh logic
- OAuth flow end-to-end
- File sync with real embeddings

## Dependencies Added
- `redis==5.0.1` (for tests)
- `aiohttp==3.9.5` (for async HTTP)
- `google-auth==2.32.0`
- `google-auth-oauthlib==1.2.0`
- `google-api-python-client==2.137.0`

## Environment Variables
```bash
# Google OAuth (configured)
GOOGLE_CLIENT_ID=741796279744-ed8polbgfqjttqt2vlpgmofs7gho8kbl.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=***hidden***
GOOGLE_REDIRECT_URI=http://localhost:8001/api/v1/gdrive/callback

# Encryption (for token storage)
ENCRYPTION_KEY=test-encryption-key  # Should be strong in production
```

## Known Issues & Workarounds

1. **Python 3.13 Compatibility**
   - Some packages (numpy, pandas) don't support 3.13 yet
   - Temporarily disabled in requirements.txt

2. **Mock Database Fallback**
   - System falls back to mock DB if PostgreSQL unavailable
   - Good for testing, but user should use real PostgreSQL

3. **OpenAI Embeddings**
   - Currently using mock key
   - User needs real OpenAI API key for embeddings

## Success Metrics
- ✅ Google Drive authentication works
- ✅ Files can be listed and synced
- ✅ Memories stored in PostgreSQL
- ✅ Code quality 10/10
- ✅ Tests passing
- ❌ Tokens persist across restarts (TODO)
- ❌ Automatic token refresh (TODO)

## Next Session Goals
1. Implement token persistence with encryption
2. Add refresh token logic
3. Test full flow with restart
4. Document token security model
5. Consider adding progress indicators for large file syncs