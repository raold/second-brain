#!/usr/bin/env python
"""
Simple demo server for Google Drive integration
Works around dependency issues to show the UI
"""

import os
import sys
import json
from pathlib import Path
from http.server import HTTPServer, SimpleHTTPRequestHandler
import webbrowser
import time

# Configuration
PORT = 8001
UI_FILE = "static/gdrive-ui.html"

class GDriveHandler(SimpleHTTPRequestHandler):
    """Custom handler for serving Google Drive UI"""
    
    def end_headers(self):
        # Add CORS headers for API testing
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        super().end_headers()
    
    def do_GET(self):
        """Handle GET requests"""
        if self.path == '/':
            self.path = '/static/gdrive-ui.html'
        elif self.path == '/api/gdrive/status':
            # Mock API response
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            response = {
                "connected": False,
                "user_email": None,
                "requires_reauth": False,
                "demo_mode": True,
                "message": "Running in demo mode - backend not fully connected"
            }
            self.wfile.write(json.dumps(response).encode())
            return
        elif self.path == '/api/gdrive/connect':
            # Mock OAuth URL
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            response = {
                "auth_url": "https://accounts.google.com/oauth2/auth?demo=true",
                "state": "demo_state_123",
                "message": "Demo mode - would redirect to Google OAuth"
            }
            self.wfile.write(json.dumps(response).encode())
            return
            
        # Serve static files
        return super().do_GET()
    
    def log_message(self, format, *args):
        """Custom log format"""
        if '/api/' in args[0]:
            print(f"🔄 API: {args[0]}")
        elif '.html' in args[0] or args[0] == '/':
            print(f"📄 Page: {args[0]}")
        elif '.css' in args[0]:
            print(f"🎨 Style: {args[0]}")
        elif '.js' in args[0]:
            print(f"⚡ Script: {args[0]}")

def check_files():
    """Check if required files exist"""
    required_files = [
        "static/gdrive-ui.html",
        "static/css/gdrive-ui.css",
        "static/js/gdrive-ui.js"
    ]
    
    missing = []
    for file in required_files:
        if not os.path.exists(file):
            missing.append(file)
    
    if missing:
        print("❌ Missing required files:")
        for file in missing:
            print(f"   - {file}")
        return False
    
    return True

def main():
    """Start the demo server"""
    print("=" * 60)
    print("🚀 Google Drive Integration Demo Server")
    print("=" * 60)
    
    # Check files
    if not check_files():
        print("\n⚠️  Some files are missing. The UI may not work properly.")
        response = input("Continue anyway? (y/n): ")
        if response.lower() != 'y':
            sys.exit(1)
    
    # Change to project directory
    os.chdir(Path(__file__).parent)
    
    # Start server
    print(f"\n📡 Starting server on http://localhost:{PORT}")
    print("=" * 60)
    
    try:
        httpd = HTTPServer(('localhost', PORT), GDriveHandler)
        
        # Print access information
        print(f"\n✅ Server running!")
        print(f"\n📌 Access points:")
        print(f"   • Main UI: http://localhost:{PORT}/static/gdrive-ui.html")
        print(f"   • API Status: http://localhost:{PORT}/api/gdrive/status")
        print(f"   • Documentation: http://localhost:{PORT}/static/api-documentation.html")
        print(f"\n💡 Press Ctrl+C to stop the server")
        print("=" * 60)
        
        # Open browser after a short delay
        def open_browser():
            time.sleep(1)
            webbrowser.open(f'http://localhost:{PORT}/static/gdrive-ui.html')
        
        import threading
        threading.Thread(target=open_browser, daemon=True).start()
        
        # Serve forever
        httpd.serve_forever()
        
    except KeyboardInterrupt:
        print("\n\n🛑 Server stopped")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()