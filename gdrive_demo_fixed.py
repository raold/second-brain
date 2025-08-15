#!/usr/bin/env python
"""
Fixed Google Drive Demo Server - Properly handles API calls
"""

import os
import json
import uuid
from http.server import HTTPServer, SimpleHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
import webbrowser
import threading
import time

PORT = 8001

class GDriveDemoHandler(SimpleHTTPRequestHandler):
    """Handler that properly mimics the Google Drive API"""
    
    def do_GET(self):
        """Handle GET requests with proper API responses"""
        parsed_path = urlparse(self.path)
        path = parsed_path.path
        
        # Route API calls
        if path.startswith('/api/v1/gdrive'):
            self.handle_api_request(path, parsed_path.query)
            return
        
        # Redirect root to the UI
        if path == '/':
            self.send_response(302)
            self.send_header('Location', '/static/gdrive-ui.html')
            self.end_headers()
            return
            
        # Serve static files
        return super().do_GET()
    
    def do_POST(self):
        """Handle POST requests"""
        parsed_path = urlparse(self.path)
        path = parsed_path.path
        
        if path.startswith('/api/v1/gdrive'):
            self.handle_api_request(path, parsed_path.query, method='POST')
            return
            
        self.send_error(404)
    
    def handle_api_request(self, path, query_string, method='GET'):
        """Handle API requests with proper JSON responses"""
        
        # Remove the base path
        endpoint = path.replace('/api/v1/gdrive', '')
        
        # Status check
        if endpoint == '/status' or endpoint == '/status/':
            self.send_json_response({
                "connected": False,
                "user_email": None,
                "last_checked": "2024-01-15T10:00:00Z",
                "storage_quota": {
                    "usage": 0,
                    "limit": 15000000000,
                    "usage_in_drive": 0
                },
                "requires_reauth": False,
                "demo_mode": True
            })
            return
        
        # Connect/OAuth initiation
        if endpoint == '/connect' or endpoint == '/connect/':
            self.send_json_response({
                "auth_url": "https://accounts.google.com/o/oauth2/v2/auth?client_id=demo&redirect_uri=http://localhost:8001/gdrive/callback&response_type=code&scope=https://www.googleapis.com/auth/drive.readonly&state=" + str(uuid.uuid4()),
                "state": str(uuid.uuid4()),
                "expires_in": 600,
                "message": "Demo mode - in production this would redirect to Google"
            })
            return
        
        # List folders
        if endpoint == '/folders' or endpoint == '/folders/':
            self.send_json_response({
                "folders": [
                    {
                        "id": "folder1",
                        "name": "Documents",
                        "path": "/Documents",
                        "mimeType": "application/vnd.google-apps.folder",
                        "size": 0,
                        "children": [
                            {"id": "doc1", "name": "Report.pdf", "size": 1024000},
                            {"id": "doc2", "name": "Presentation.pptx", "size": 2048000}
                        ]
                    },
                    {
                        "id": "folder2",
                        "name": "Projects",
                        "path": "/Projects",
                        "mimeType": "application/vnd.google-apps.folder",
                        "size": 0,
                        "children": []
                    }
                ],
                "total_files": 25,
                "total_size": 104857600
            })
            return
        
        # Sync endpoint
        if endpoint.startswith('/sync'):
            task_id = str(uuid.uuid4())
            self.send_json_response({
                "task_id": task_id,
                "status": "queued",
                "message": "Sync task created (demo mode)",
                "estimated_time": 30
            })
            return
        
        # OAuth callback
        if endpoint == '/callback':
            self.send_response(200)
            self.send_header('Content-Type', 'text/html')
            self.end_headers()
            html = """
            <html>
            <head>
                <title>Google Drive Connected</title>
                <style>
                    body { font-family: sans-serif; display: flex; justify-content: center; align-items: center; height: 100vh; }
                    .message { text-align: center; }
                </style>
            </head>
            <body>
                <div class="message">
                    <h1>✅ Google Drive Connected (Demo)</h1>
                    <p>You can close this window and return to the application.</p>
                    <script>
                        setTimeout(() => { window.close(); }, 3000);
                    </script>
                </div>
            </body>
            </html>
            """
            self.wfile.write(html.encode())
            return
        
        # Default 404
        self.send_error(404, f"Endpoint not found: {endpoint}")
    
    def send_json_response(self, data, status=200):
        """Send a JSON response"""
        self.send_response(status)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(json.dumps(data).encode())
    
    def end_headers(self):
        """Add CORS headers"""
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        super().end_headers()
    
    def log_message(self, format, *args):
        """Custom logging"""
        if len(args) > 0 and isinstance(args[0], str):
            request = args[0]
            if '/api/' in request:
                print(f"🔄 API: {request}")
            elif '.html' in request or request == 'GET / ':
                print(f"📄 Page: {request}")
            elif '.css' in request:
                print(f"🎨 Style: {request}")
            elif '.js' in request:
                print(f"⚡ Script: {request}")
            elif 'favicon' in request:
                return  # Skip favicon logs
            else:
                print(f"📁 File: {request}")

def check_ui_files():
    """Check if UI files exist"""
    required = [
        "static/gdrive-ui.html",
        "static/css/gdrive-ui.css",
        "static/js/gdrive-ui.js"
    ]
    
    for file in required:
        if not os.path.exists(file):
            print(f"⚠️  Missing: {file}")
            return False
    return True

def open_browser_delayed():
    """Open browser after server starts"""
    time.sleep(1.5)
    webbrowser.open(f'http://localhost:{PORT}/static/gdrive-ui.html')

def main():
    print("=" * 60)
    print("🚀 Google Drive Integration Demo (Fixed)")
    print("=" * 60)
    
    if not check_ui_files():
        print("\n❌ Required UI files missing!")
        return
    
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    
    try:
        server = HTTPServer(('localhost', PORT), GDriveDemoHandler)
        
        print(f"\n✅ Server running on http://localhost:{PORT}")
        print(f"\n📌 Access points:")
        print(f"   • Main UI: http://localhost:{PORT}/static/gdrive-ui.html")
        print(f"   • API Status: http://localhost:{PORT}/api/v1/gdrive/status")
        print(f"\n🎯 The 'Connect Google Drive' button will now work!")
        print(f"   (Shows demo OAuth flow - no real Google connection)")
        print(f"\n💡 Press Ctrl+C to stop")
        print("=" * 60)
        
        # Open browser
        threading.Thread(target=open_browser_delayed, daemon=True).start()
        
        server.serve_forever()
        
    except KeyboardInterrupt:
        print("\n\n🛑 Server stopped")
    except OSError as e:
        if "Address already in use" in str(e):
            print(f"\n❌ Port {PORT} is already in use!")
            print("   Run: lsof -ti:8001 | xargs kill -9")
        else:
            print(f"\n❌ Error: {e}")

if __name__ == "__main__":
    main()