#!/usr/bin/env python3
"""
Simple dashboard server for Second Brain with real git visualization.
This serves the dashboard with real git data without complex database setup.
"""

import json
import subprocess
import webbrowser
from http.server import HTTPServer, SimpleHTTPRequestHandler
from pathlib import Path
from urllib.parse import urlparse


class DashboardHandler(SimpleHTTPRequestHandler):
    """Custom handler for dashboard requests."""

    def __init__(self, *args, **kwargs):
        # Set the directory to serve files from
        self.directory = str(Path(__file__).parent / "static")
        super().__init__(*args, directory=self.directory, **kwargs)

    def do_GET(self):
        """Handle GET requests."""
        parsed_path = urlparse(self.path)

        # Handle API endpoints for git data
        if parsed_path.path.startswith('/dashboard/git/'):
            self.handle_git_api(parsed_path.path)
        # Handle development status API - HIGH PRIORITY
        elif parsed_path.path == '/dashboard/development/status':
            self.handle_development_status_api()
        # Handle project data API
        elif parsed_path.path == '/dashboard/project/data':
            self.handle_project_api()
        # Handle branch switching API
        elif parsed_path.path.startswith('/api/branches/'):
            self.handle_branch_api(parsed_path.path, parsed_path.query)
        # Handle mock database data
        elif parsed_path.path.startswith('/dashboard_data/'):
            self.handle_static_file(parsed_path.path)
        elif parsed_path.path == '/':
            # Serve the main dashboard
            self.serve_dashboard()
        else:
            # Serve static files
            super().do_GET()

    def handle_git_api(self, path):
        """Handle git API endpoints."""
        try:
            if path == '/dashboard/git/repository-status':
                data = self.get_git_status()
            elif path == '/dashboard/git/visualization':
                data = self.get_git_visualization()
            elif path == '/dashboard/git/commit-activity':
                data = self.get_commit_activity()
            else:
                self.send_error(404, "API endpoint not found")
                return

            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(json.dumps(data).encode())

        except Exception as e:
            self.send_error(500, f"Error: {str(e)}")

    def handle_development_status_api(self):
        """Handle development status API requests - HIGH PRIORITY."""
        try:
            # Import and use the development status module
            import development_status
            status_data = development_status.get_development_status()

            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(json.dumps(status_data).encode('utf-8'))

        except Exception as e:
            # Provide fallback development status data
            fallback_data = {
                "error": f"Development status error: {str(e)}",
                "fallback": True,
                "timestamp": "2025-07-19T08:00:00",
                "summary": {
                    "current_version": "2.4.3",
                    "next_version": "2.5.0",
                    "total_branches": 7,
                    "active_features": 3,
                    "ready_for_pr": 2
                },
                "branches": [
                    {"name": "main", "current": True, "status": "Stable", "progress": 100},
                    {"name": "develop", "current": False, "status": "Active", "progress": 75},
                    {"name": "feature/project-pipeline", "current": False, "status": "In Progress", "progress": 60}
                ]
            }
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(json.dumps(fallback_data).encode('utf-8'))

    def handle_project_api(self):
        """Handle project data API requests."""
        try:
            project_data_path = Path(__file__).parent / "dashboard_data" / "project_data.json"
            if project_data_path.exists():
                with open(project_data_path, encoding='utf-8') as f:
                    data = json.load(f)
            else:
                # Provide fallback data if file doesn't exist
                data = {
                    "project_info": {
                        "name": "Second Brain v2.4.3",
                        "completion_percentage": 46,
                        "status": "In Development"
                    },
                    "error": "Project data file not found - using fallback"
                }

            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(json.dumps(data, ensure_ascii=False).encode('utf-8'))

        except Exception as e:
            # Send error response instead of hanging
            error_data = {"error": f"Error loading project data: {str(e)}"}
            self.send_response(500)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(json.dumps(error_data).encode('utf-8'))

    def handle_branch_api(self, path, query):
        """Handle branch switching API requests."""
        try:
            # Parse branch name from path: /api/branches/{branch_name}
            parts = path.split('/')
            if len(parts) < 4:
                self.send_error(400, "Invalid branch API path")
                return

            branch_name = parts[3]

            # Load git data
            git_data_path = Path(__file__).parent / "dashboard_data" / "git_data.json"
            if git_data_path.exists():
                with open(git_data_path) as f:
                    git_data = json.load(f)

                # Find the specific branch
                branch_info = None
                for node in git_data.get('nodes', []):
                    if node.get('id') == branch_name:
                        branch_info = node
                        break

                if branch_info:
                    self.send_response(200)
                    self.send_header('Content-type', 'application/json')
                    self.send_header('Access-Control-Allow-Origin', '*')
                    self.end_headers()
                    self.wfile.write(json.dumps(branch_info).encode())
                else:
                    self.send_error(404, f"Branch not found: {branch_name}")
            else:
                self.send_error(500, "Git data not available")

        except Exception as e:
            self.send_error(500, f"Branch API error: {str(e)}")

    def handle_static_file(self, path):
        """Handle static file requests."""
        try:
            # Remove leading slash and serve from current directory
            file_path = Path(__file__).parent / path.lstrip('/')

            if file_path.exists():
                self.send_response(200)

                # Determine content type
                if path.endswith('.json'):
                    self.send_header('Content-type', 'application/json')
                elif path.endswith('.html'):
                    self.send_header('Content-type', 'text/html')
                elif path.endswith('.css'):
                    self.send_header('Content-type', 'text/css')
                elif path.endswith('.js'):
                    self.send_header('Content-type', 'application/javascript')
                else:
                    self.send_header('Content-type', 'text/plain')

                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()

                with open(file_path, 'rb') as f:
                    self.wfile.write(f.read())
            else:
                self.send_error(404, f"File not found: {path}")
        except Exception as e:
            self.send_error(500, f"Static file error: {str(e)}")

    def get_git_status(self):
        """Get git repository status."""
        try:
            # Get current branch
            current_branch = subprocess.check_output(['git', 'branch', '--show-current'], text=True).strip()

            # Get all branches
            branches_output = subprocess.check_output(['git', 'branch', '-a'], text=True)
            branches = [b.strip().replace('* ', '').replace('remotes/', '') for b in branches_output.split('\n') if b.strip()]

            # Check for uncommitted changes
            status_output = subprocess.check_output(['git', 'status', '--porcelain'], text=True)
            has_uncommitted = bool(status_output.strip())

            return {
                "current_branch": current_branch,
                "total_branches": len(branches),
                "has_uncommitted_changes": has_uncommitted,
                "branches": branches[:10]  # Limit for display
            }
        except Exception as e:
            return {"error": f"Git status error: {str(e)}"}

    def get_git_visualization(self):
        """Get git visualization data."""
        try:
            # Load from git_data.json if exists
            git_data_path = Path(__file__).parent / "dashboard_data" / "git_data.json"
            if git_data_path.exists():
                with open(git_data_path) as f:
                    return json.load(f)
            else:
                # Generate fresh data
                self.generate_git_data()
                if git_data_path.exists():
                    with open(git_data_path) as f:
                        return json.load(f)
                else:
                    return {"nodes": [], "links": [], "error": "Could not generate git data"}
        except Exception as e:
            return {"error": f"Visualization error: {str(e)}"}

    def get_commit_activity(self):
        """Get commit activity metrics."""
        try:
            # Run git demo to get fresh metrics
            self.generate_git_data()

            # Load from git_data.json if exists
            git_data_path = Path(__file__).parent / "dashboard_data" / "git_data.json"
            if git_data_path.exists():
                with open(git_data_path) as f:
                    git_data = json.load(f)

                # Extract repository-wide activity summary
                repository_summary = {}
                for period in ['24h', '7d', '30d']:
                    total_commits = 0
                    total_lines_added = 0
                    total_lines_deleted = 0
                    total_files_changed = 0
                    authors = set()

                    for node in git_data.get('nodes', []):
                        metrics_key = f'metrics_{period}'
                        if metrics_key in node:
                            metrics = node[metrics_key]
                            total_commits += metrics.get('commit_count', 0)
                            total_lines_added += metrics.get('lines_added', 0)
                            total_lines_deleted += metrics.get('lines_deleted', 0)
                            total_files_changed += metrics.get('files_changed', 0)
                            authors.update(metrics.get('authors', []))

                    repository_summary[period] = {
                        "commits": total_commits,
                        "lines_added": total_lines_added,
                        "lines_deleted": total_lines_deleted,
                        "files_changed": total_files_changed,
                        "authors": len(authors)
                    }

                # Extract per-branch activity
                branch_activity = {}
                for node in git_data.get('nodes', []):
                    branch_name = node.get('id', 'unknown')
                    branch_activity[branch_name] = {
                        'status': node.get('status', 'unknown'),
                        'features': node.get('features', []),
                        'commit_info': node.get('commit_info', ''),
                        'is_current': node.get('is_current', False),
                        'metrics': {
                            '24h': node.get('metrics_24h', {}),
                            '7d': node.get('metrics_7d', {}),
                            '30d': node.get('metrics_30d', {})
                        }
                    }

                return {
                    "repository_summary": repository_summary,
                    "branch_activity": branch_activity
                }
            else:
                # Fallback to simple git commands
                periods = {'24h': '1 day ago', '7d': '1 week ago', '30d': '1 month ago'}
                activity = {}

                for period, since in periods.items():
                    try:
                        # Get commit count
                        commit_count = subprocess.check_output(
                            ['git', 'log', f'--since={since}', '--oneline'],
                            text=True
                        ).count('\n')

                        # Get lines added/deleted
                        stats = subprocess.check_output(
                            ['git', 'log', f'--since={since}', '--numstat', '--pretty=format:'],
                            text=True
                        )

                        lines_added = 0
                        lines_deleted = 0
                        for line in stats.split('\n'):
                            if line.strip() and '\t' in line:
                                parts = line.split('\t')
                                if len(parts) >= 2 and parts[0].isdigit() and parts[1].isdigit():
                                    lines_added += int(parts[0])
                                    lines_deleted += int(parts[1])

                        activity[period] = {
                            "commits": commit_count,
                            "lines_added": lines_added,
                            "lines_deleted": lines_deleted,
                            "files_changed": 0,
                            "authors": 1
                        }
                    except:
                        activity[period] = {"commits": 0, "lines_added": 0, "lines_deleted": 0, "files_changed": 0, "authors": 0}

                return {
                    "repository_summary": activity,
                    "branch_activity": {}
                }
        except Exception as e:
            return {"error": f"Activity error: {str(e)}"}

    def generate_git_data(self):
        """Generate fresh git data using git_demo.py."""
        try:
            subprocess.run(['python', 'git_demo.py'], check=True)
        except Exception as e:
            print(f"Error generating git data: {e}")

    def serve_dashboard(self):
        """Serve the main dashboard HTML."""
        try:
            # Use the Tufte-inspired dashboard
            dashboard_path = Path(__file__).parent / "tufte_dashboard.html"

            if dashboard_path.exists():
                self.send_response(200)
                self.send_header('Content-type', 'text/html')
                self.end_headers()
                with open(dashboard_path, 'rb') as f:
                    self.wfile.write(f.read())
            else:
                self.send_error(404, "Tufte dashboard not found")
        except Exception as e:
            self.send_error(500, f"Dashboard error: {str(e)}")


def main():
    """Start the simple dashboard server."""
    port = 8000

    print("🚀 Starting Second Brain Dashboard Server")
    print("📊 Real Git Visualization Enabled")
    print(f"🌐 Server running at: http://localhost:{port}")

    # Generate fresh git data
    try:
        print("📈 Generating fresh git data...")
        subprocess.run(['python', 'git_demo.py'], check=True)
        print("✅ Git data generated successfully")
    except Exception as e:
        print(f"⚠️ Warning: Could not generate git data: {e}")

    try:
        httpd = HTTPServer(('localhost', port), DashboardHandler)
        print("✅ Dashboard ready! Opening browser...")

        # Open browser automatically
        webbrowser.open(f'http://localhost:{port}')

        print("Press Ctrl+C to stop the server")
        httpd.serve_forever()

    except KeyboardInterrupt:
        print("\n🛑 Server stopped")
    except Exception as e:
        print(f"❌ Server error: {e}")


if __name__ == "__main__":
    main()
