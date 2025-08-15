#!/usr/bin/env python3
"""
Google OAuth Setup Helper for Second Brain v4.2.3
This script helps you quickly set up Google OAuth credentials
"""

import os
import json
import webbrowser
from pathlib import Path

def setup_google_oauth():
    print("=" * 60)
    print("🔐 Google OAuth Setup for Second Brain")
    print("=" * 60)
    print()
    
    # Check if .env exists
    env_path = Path(".env")
    if not env_path.exists():
        print("⚠️  No .env file found. Creating from template...")
        template_path = Path(".env.example")
        if template_path.exists():
            env_content = template_path.read_text()
        else:
            env_content = """# Google OAuth Configuration (add your credentials here)
GOOGLE_CLIENT_ID=
GOOGLE_CLIENT_SECRET=
GOOGLE_REDIRECT_URI=http://localhost:8001/api/v1/gdrive/callback

# Database
USE_MOCK_DATABASE=true
DATABASE_URL=postgresql://user:password@localhost/secondbrain

# OpenAI (optional)
OPENAI_API_KEY=sk-mock-key-for-testing-only

# Application
APP_ENV=development
PORT=8001
JWT_SECRET_KEY=test-secret-key
ENCRYPTION_KEY=test-encryption-key
"""
        env_path.write_text(env_content)
        print("✅ Created .env file")
    
    # Read current .env
    env_content = env_path.read_text()
    
    print("📋 Current Google OAuth Configuration:")
    print("-" * 40)
    
    # Check current values
    has_client_id = False
    has_client_secret = False
    
    for line in env_content.split('\n'):
        if line.startswith('GOOGLE_CLIENT_ID=') and len(line) > 17:
            has_client_id = True
            print(f"✅ Client ID: {line[17:37]}...")
        elif line.startswith('GOOGLE_CLIENT_SECRET=') and len(line) > 21:
            has_client_secret = True
            print(f"✅ Client Secret: ****")
    
    if not has_client_id:
        print("❌ Client ID: Not configured")
    if not has_client_secret:
        print("❌ Client Secret: Not configured")
    
    print()
    
    if has_client_id and has_client_secret:
        print("✅ Google OAuth is already configured!")
        print()
        print("🚀 Next steps:")
        print("1. Restart the application if it's running")
        print("2. Open http://localhost:8001/static/gdrive-ui.html")
        print("3. Click 'Connect Google Drive'")
        return
    
    print("📝 To set up Google OAuth, you need to:")
    print()
    print("1. Go to Google Cloud Console")
    print("2. Create OAuth 2.0 credentials")
    print("3. Add the credentials to your .env file")
    print()
    
    choice = input("Would you like to open Google Cloud Console now? (y/n): ")
    if choice.lower() == 'y':
        print()
        print("Opening Google Cloud Console...")
        webbrowser.open("https://console.cloud.google.com/apis/credentials")
        print()
        print("📋 Quick Setup Instructions:")
        print("-" * 40)
        print("1. Create a new project or select existing")
        print("2. Click 'CREATE CREDENTIALS' → 'OAuth 2.0 Client ID'")
        print("3. Application type: Web application")
        print("4. Add authorized redirect URI:")
        print("   http://localhost:8001/api/v1/gdrive/callback")
        print("5. Copy the Client ID and Client Secret")
        print()
    
    print("📝 Enter your Google OAuth credentials:")
    print("(Leave blank to skip)")
    print()
    
    client_id = input("Client ID: ").strip()
    client_secret = input("Client Secret: ").strip()
    
    if client_id and client_secret:
        # Update .env file
        lines = env_content.split('\n')
        for i, line in enumerate(lines):
            if line.startswith('GOOGLE_CLIENT_ID='):
                lines[i] = f'GOOGLE_CLIENT_ID={client_id}'
            elif line.startswith('GOOGLE_CLIENT_SECRET='):
                lines[i] = f'GOOGLE_CLIENT_SECRET={client_secret}'
        
        env_path.write_text('\n'.join(lines))
        print()
        print("✅ Credentials saved to .env file!")
        print()
        print("🚀 Next steps:")
        print("1. Start the application: ./start_with_gdrive.sh")
        print("2. Open http://localhost:8001/static/gdrive-ui.html")
        print("3. Click 'Connect Google Drive'")
    else:
        print()
        print("⚠️  No credentials entered. You can add them manually to .env file")
        print()
        print("Add these lines to your .env file:")
        print(f"GOOGLE_CLIENT_ID=your-client-id")
        print(f"GOOGLE_CLIENT_SECRET=your-client-secret")

if __name__ == "__main__":
    setup_google_oauth()