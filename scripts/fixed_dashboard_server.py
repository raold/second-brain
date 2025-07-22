#!/usr/bin/env python3
"""
Fixed Dashboard Server - Reliable Development Status Display
Serves the Tufte dashboard with proper development status API
"""

import http.server
import json
import os
import socketserver
import sys
from pathlib import Path
from urllib.parse import urlparse

# Fix Windows console encoding issues
if sys.platform == 'win32':
    os.system('chcp 65001 >nul 2>&1')  # Set console to UTF-8

class FixedDashboardHandler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        parsed_path = urlparse(self.path)

        print(f"[REQ] Request: {parsed_path.path}")

        # Handle development status API - HIGH PRIORITY
        if parsed_path.path == '/dashboard/development/status':
            self.handle_development_status()
        # Serve tufte dashboard
        elif parsed_path.path == '/tufte_dashboard.html' or parsed_path.path == '/':
            self.serve_dashboard()
        # Handle static files
        else:
            super().do_GET()

    def handle_development_status(self):
        """Handle development status API - provides real data"""
        try:
            print("[*] Loading development status...")

            # Import development status
            import development_status
            status_data = development_status.get_development_status()

            print("[OK] Development status loaded successfully")
            print(f"[DATA] Data keys: {list(status_data.keys())}")
            print(f"[FEAT] Features count: {len(status_data.get('features', []))}")
            print(f"[PR] PR status count: {len(status_data.get('pr_status', []))}")

            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()

            # Send the data
            json_data = json.dumps(status_data, indent=2)
            self.wfile.write(json_data.encode('utf-8'))

        except Exception as e:
            print(f"[ERR] Error loading development status: {e}")
            import traceback
            traceback.print_exc()

            # Send error response
            error_data = {
                "error": f"Development status error: {str(e)}",
                "fallback_summary": {
                    "current_version": "v2.4.3",
                    "next_version": "v2.5.0",
                    "total_branches": 7,
                    "ready_for_pr": 1
                },
                "fallback_pr_status": [
                    {
                        "branch": "main",
                        "feature": "Production Release",
                        "version": "2.4.3",
                        "progress": 100,
                        "status": "Complete",
                        "pr_ready": "Deployed",
                        "priority": "High"
                    }
                ],
                "fallback_version_roadmap": {
                    "v2.4.3": {
                        "status": "Production Ready",
                        "release_date": "2025-08-30",
                        "focus": "Quality Excellence & Git Visualization",
                        "completion": 100,
                        "key_technologies": ["Edward Tufte principles", "Git visualization"]
                    },
                    "v2.5.0": {
                        "status": "Planned",
                        "release_date": "2025-10-15",
                        "focus": "Memory Architecture Foundation",
                        "completion": 35,
                        "key_technologies": ["Multi-hop reasoning", "Pattern recognition"]
                    }
                }
            }

            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(json.dumps(error_data).encode('utf-8'))

    def serve_dashboard(self):
        """Serve the Tufte dashboard"""
        dashboard_path = Path(__file__).parent / "tufte_dashboard.html"

        if dashboard_path.exists():
            self.send_response(200)
            self.send_header('Content-Type', 'text/html')
            self.end_headers()

            with open(dashboard_path, encoding='utf-8') as f:
                self.wfile.write(f.read().encode('utf-8'))
        else:
            self.send_error(404, "Dashboard not found")

def main():
    PORT = 8000

    print("[*] Starting Fixed Second Brain Dashboard Server")
    print(f"[*] Server running at: http://localhost:{PORT}")
    print("[*] Development Status API: /dashboard/development/status")
    print("[*] Tufte Dashboard: http://localhost:8000/tufte_dashboard.html")

    os.chdir(Path(__file__).parent)

    with socketserver.TCPServer(("", PORT), FixedDashboardHandler) as httpd:
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\n[*] Server stopped")

if __name__ == "__main__":
    main()
