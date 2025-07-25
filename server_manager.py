#!/usr/bin/env python3
"""
Second Brain Dashboard Server Manager
Provides clean start, stop, restart, and status functionality
"""

import argparse
import os
import subprocess
import sys
import time
from pathlib import Path

import psutil


class DashboardServerManager:
    def __init__(self):
        self.server_script = "fixed_dashboard_server.py"
        self.port = 8000
        self.pid_file = Path("dashboard_server.pid")
        self.log_file = Path("dashboard_server.log")

    def find_process_by_port(self, port):
        """Find process using the specified port"""
        for proc in psutil.process_iter(['pid', 'name', 'connections']):
            try:
                for conn in proc.info['connections'] or []:
                    if conn.laddr.port == port:
                        return proc.info['pid']
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                pass
        return None

    def find_python_dashboard_processes(self):
        """Find all Python processes running dashboard server"""
        processes = []
        for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
            try:
                if (proc.info['name'] and 'python' in proc.info['name'].lower() and
                    proc.info['cmdline'] and any('dashboard_server' in arg for arg in proc.info['cmdline'])):
                    processes.append(proc.info['pid'])
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                pass
        return processes

    def is_server_running(self):
        """Check if the dashboard server is currently running"""
        # Check by PID file
        if self.pid_file.exists():
            try:
                with open(self.pid_file) as f:
                    pid = int(f.read().strip())
                if psutil.pid_exists(pid):
                    return pid
                else:
                    # PID file exists but process is dead, clean it up
                    self.pid_file.unlink()
            except (ValueError, FileNotFoundError):
                pass

        # Check by port
        port_pid = self.find_process_by_port(self.port)
        if port_pid:
            return port_pid

        # Check by process name
        dashboard_pids = self.find_python_dashboard_processes()
        if dashboard_pids:
            return dashboard_pids[0]

        return None

    def stop_server(self, force=False):
        """Stop the dashboard server"""
        print("[STOP] Stopping dashboard server...")

        # Find all possible server processes
        processes_to_stop = []

        # Add PID from file
        running_pid = self.is_server_running()
        if running_pid:
            processes_to_stop.append(running_pid)

        # Add processes by port
        port_pid = self.find_process_by_port(self.port)
        if port_pid and port_pid not in processes_to_stop:
            processes_to_stop.append(port_pid)

        # Add dashboard processes
        dashboard_pids = self.find_python_dashboard_processes()
        for pid in dashboard_pids:
            if pid not in processes_to_stop:
                processes_to_stop.append(pid)

        if not processes_to_stop:
            print("[OK] No dashboard server processes found running")
            # Clean up stale PID file
            if self.pid_file.exists():
                self.pid_file.unlink()
            return True

        # Stop each process
        stopped = []
        for pid in processes_to_stop:
            try:
                proc = psutil.Process(pid)
                print(f"   Stopping PID {pid}: {' '.join(proc.cmdline())}")

                if force:
                    proc.kill()  # SIGKILL
                else:
                    proc.terminate()  # SIGTERM

                # Wait for process to stop
                try:
                    proc.wait(timeout=5)
                    stopped.append(pid)
                    print(f"   [OK] Stopped PID {pid}")
                except psutil.TimeoutExpired:
                    if not force:
                        print(f"   ⚠️ PID {pid} didn't stop gracefully, forcing...")
                        proc.kill()
                        proc.wait(timeout=2)
                        stopped.append(pid)
                        print(f"   [OK] Force stopped PID {pid}")
                    else:
                        print(f"   [ERR] Failed to stop PID {pid}")

            except (psutil.NoSuchProcess, psutil.AccessDenied) as e:
                print(f"   ⚠️ Could not stop PID {pid}: {e}")

        # Clean up PID file
        if self.pid_file.exists():
            self.pid_file.unlink()

        print(f"[OK] Stopped {len(stopped)} dashboard server process(es)")
        return len(stopped) == len(processes_to_stop)

    def start_server(self):
        """Start the dashboard server"""
        print("[START] Starting dashboard server...")

        # Check if already running
        if self.is_server_running():
            print("[ERR] Dashboard server is already running")
            print("   Use 'restart' to restart or 'stop' to stop first")
            return False

        # Ensure script exists
        if not Path(self.server_script).exists():
            print(f"[ERR] Server script not found: {self.server_script}")
            return False

        try:
            # Start server as background process
            with open(self.log_file, 'w') as log:
                process = subprocess.Popen(
                    [sys.executable, self.server_script],
                    stdout=log,
                    stderr=subprocess.STDOUT,
                    cwd=os.getcwd()
                )

            # Save PID
            with open(self.pid_file, 'w') as f:
                f.write(str(process.pid))

            # Wait a moment and check if it started successfully
            time.sleep(2)

            if self.is_server_running():
                print("[OK] Dashboard server started successfully")
                print(f"   PID: {process.pid}")
                print(f"   URL: http://localhost:{self.port}")
                print(f"   Dashboard: http://localhost:{self.port}/tufte_dashboard.html")
                print(f"   Logs: {self.log_file}")
                return True
            else:
                print("[ERR] Server failed to start")
                # Show recent logs
                if self.log_file.exists():
                    print("Recent logs:")
                    with open(self.log_file) as f:
                        lines = f.readlines()[-10:]  # Last 10 lines
                        for line in lines:
                            print(f"   {line.rstrip()}")
                return False

        except Exception as e:
            print(f"[ERR] Error starting server: {e}")
            return False

    def restart_server(self):
        """Restart the dashboard server"""
        print("[RESTART] Restarting dashboard server...")

        # Stop first
        self.stop_server()

        # Wait a moment
        time.sleep(1)

        # Start again
        return self.start_server()

    def status(self):
        """Show server status"""
        print("[STATUS] Dashboard Server Status")
        print("=" * 50)

        running_pid = self.is_server_running()
        if running_pid:
            try:
                proc = psutil.Process(running_pid)
                print("Status: [RUNNING]")
                print(f"PID: {running_pid}")
                print(f"Command: {' '.join(proc.cmdline())}")
                print(f"Started: {time.ctime(proc.create_time())}")
                print(f"CPU: {proc.cpu_percent():.1f}%")
                print(f"Memory: {proc.memory_info().rss / 1024 / 1024:.1f} MB")
                print(f"URL: http://localhost:{self.port}")
                print(f"Dashboard: http://localhost:{self.port}/tufte_dashboard.html")
            except psutil.NoSuchProcess:
                print(f"Status: [DEAD] PROCESS DEAD (PID {running_pid})")
        else:
            print("Status: [NOT RUNNING]")

        # Check port availability
        port_pid = self.find_process_by_port(self.port)
        if port_pid and port_pid != running_pid:
            print(f"[WARN] Port {self.port} is occupied by PID {port_pid}")

        # Show log file info
        if self.log_file.exists():
            stat = self.log_file.stat()
            print(f"Log file: {self.log_file} ({stat.st_size} bytes)")
        else:
            print("Log file: Not found")

    def logs(self, lines=20):
        """Show recent server logs"""
        print(f"[LOGS] Dashboard Server Logs (last {lines} lines)")
        print("=" * 50)

        if not self.log_file.exists():
            print("[ERR] Log file not found")
            return

        try:
            with open(self.log_file) as f:
                all_lines = f.readlines()
                recent_lines = all_lines[-lines:] if len(all_lines) > lines else all_lines

            for line in recent_lines:
                print(line.rstrip())

        except Exception as e:
            print(f"[ERR] Error reading log file: {e}")

def main():
    parser = argparse.ArgumentParser(description="Second Brain Dashboard Server Manager")
    parser.add_argument('action', choices=['start', 'stop', 'restart', 'status', 'logs'],
                       help='Action to perform')
    parser.add_argument('--force', action='store_true',
                       help='Force stop (SIGKILL instead of SIGTERM)')
    parser.add_argument('--lines', type=int, default=20,
                       help='Number of log lines to show (default: 20)')

    args = parser.parse_args()

    manager = DashboardServerManager()

    try:
        if args.action == 'start':
            success = manager.start_server()
            sys.exit(0 if success else 1)

        elif args.action == 'stop':
            success = manager.stop_server(force=args.force)
            sys.exit(0 if success else 1)

        elif args.action == 'restart':
            success = manager.restart_server()
            sys.exit(0 if success else 1)

        elif args.action == 'status':
            manager.status()

        elif args.action == 'logs':
            manager.logs(lines=args.lines)

    except KeyboardInterrupt:
        print("\n[WARN] Interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"[ERR] Unexpected error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
