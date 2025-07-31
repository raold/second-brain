#!/usr/bin/env python3
"""
Docker services management script for Second Brain application.
Provides easy commands to start, stop, and monitor database services.
"""

import subprocess
import sys
import time
from pathlib import Path
from typing import List, Optional

import click


def run_command(cmd: List[str], capture_output: bool = False) -> subprocess.CompletedProcess:
    """Run a command and return the result."""
    try:
        result = subprocess.run(cmd, capture_output=capture_output, text=True, check=True)
        return result
    except subprocess.CalledProcessError as e:
        click.echo(f"❌ Command failed: {' '.join(cmd)}")
        click.echo(f"Error: {e.stderr if e.stderr else e.stdout}")
        sys.exit(1)


def check_docker() -> bool:
    """Check if Docker is installed and running."""
    try:
        result = subprocess.run(['docker', '--version'], capture_output=True, text=True)
        if result.returncode != 0:
            click.echo("❌ Docker is not installed")
            return False
        
        result = subprocess.run(['docker', 'ps'], capture_output=True, text=True)
        if result.returncode != 0:
            click.echo("❌ Docker is not running")
            return False
        
        return True
    except FileNotFoundError:
        click.echo("❌ Docker is not installed")
        return False


def check_docker_compose() -> bool:
    """Check if Docker Compose is available."""
    try:
        # Try docker compose (newer version)
        result = subprocess.run(['docker', 'compose', '--version'], capture_output=True, text=True)
        if result.returncode == 0:
            return True
        
        # Try docker-compose (older version)
        result = subprocess.run(['docker-compose', '--version'], capture_output=True, text=True)
        return result.returncode == 0
    except FileNotFoundError:
        return False


def get_compose_command() -> List[str]:
    """Get the appropriate docker compose command."""
    try:
        result = subprocess.run(['docker', 'compose', '--version'], capture_output=True, text=True)
        if result.returncode == 0:
            return ['docker', 'compose']
    except FileNotFoundError:
        pass
    
    return ['docker-compose']


def wait_for_service(service_name: str, port: int, timeout: int = 60) -> bool:
    """Wait for a service to be ready."""
    import socket
    
    click.echo(f"⏳ Waiting for {service_name} on port {port}...")
    
    start_time = time.time()
    while time.time() - start_time < timeout:
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(1)
            result = sock.connect_ex(('localhost', port))
            sock.close()
            
            if result == 0:
                click.echo(f"✅ {service_name} is ready!")
                return True
        except Exception:
            pass
        
        time.sleep(1)
    
    click.echo(f"❌ {service_name} failed to start within {timeout} seconds")
    return False


@click.group()
def cli():
    """Second Brain Database Services Manager."""
    pass


@cli.command()
@click.option('--wait', is_flag=True, help='Wait for services to be ready')
@click.option('--timeout', default=60, help='Timeout in seconds to wait for services')
def start(wait: bool, timeout: int):
    """Start database services."""
    if not check_docker():
        sys.exit(1)
    
    if not check_docker_compose():
        click.echo("❌ Docker Compose is not available")
        sys.exit(1)
    
    compose_cmd = get_compose_command()
    
    click.echo("🚀 Starting database services...")
    
    # Start services
    run_command(compose_cmd + ['up', '-d', 'qdrant', 'postgres'])
    
    if wait:
        # Wait for services to be ready
        qdrant_ready = wait_for_service('Qdrant', 6333, timeout)
        postgres_ready = wait_for_service('PostgreSQL', 5432, timeout)
        
        if qdrant_ready and postgres_ready:
            click.echo("🎉 All services are ready!")
        else:
            click.echo("⚠️  Some services may not be ready")
    
    click.echo("✅ Database services started")


@cli.command()
def stop():
    """Stop database services."""
    if not check_docker():
        sys.exit(1)
    
    if not check_docker_compose():
        click.echo("❌ Docker Compose is not available")
        sys.exit(1)
    
    compose_cmd = get_compose_command()
    
    click.echo("🛑 Stopping database services...")
    run_command(compose_cmd + ['down'])
    click.echo("✅ Database services stopped")


@cli.command()
def status():
    """Check status of database services."""
    if not check_docker():
        sys.exit(1)
    
    if not check_docker_compose():
        click.echo("❌ Docker Compose is not available")
        sys.exit(1)
    
    compose_cmd = get_compose_command()
    
    click.echo("📊 Database services status:")
    click.echo("-" * 40)
    
    try:
        result = run_command(compose_cmd + ['ps'], capture_output=True)
        click.echo(result.stdout)
    except Exception:
        click.echo("❌ Failed to get service status")


@cli.command()
def logs():
    """Show logs from database services."""
    if not check_docker():
        sys.exit(1)
    
    if not check_docker_compose():
        click.echo("❌ Docker Compose is not available")
        sys.exit(1)
    
    compose_cmd = get_compose_command()
    
    click.echo("📋 Database services logs:")
    click.echo("-" * 40)
    
    try:
        # Use subprocess.run without check=True to allow interruption
        subprocess.run(compose_cmd + ['logs', '-f', 'qdrant', 'postgres'])
    except KeyboardInterrupt:
        click.echo("\n⚠️  Logs interrupted by user")


@cli.command()
def reset():
    """Reset database services (removes all data)."""
    if not click.confirm("⚠️  This will remove all data. Are you sure?"):
        click.echo("Cancelled.")
        return
    
    if not check_docker():
        sys.exit(1)
    
    if not check_docker_compose():
        click.echo("❌ Docker Compose is not available")
        sys.exit(1)
    
    compose_cmd = get_compose_command()
    
    click.echo("🗑️  Resetting database services...")
    
    # Stop services
    run_command(compose_cmd + ['down'])
    
    # Remove volumes
    run_command(compose_cmd + ['down', '-v'])
    
    # Start services
    run_command(compose_cmd + ['up', '-d', 'qdrant', 'postgres'])
    
    # Wait for services
    qdrant_ready = wait_for_service('Qdrant', 6333, 60)
    postgres_ready = wait_for_service('PostgreSQL', 5432, 60)
    
    if qdrant_ready and postgres_ready:
        click.echo("✅ Database services reset and ready!")
    else:
        click.echo("⚠️  Services may not be ready, check logs")


@cli.command()
@click.option('--host', default='localhost', help='Database host')
@click.option('--port', default=6333, help='Qdrant port')
def test_qdrant(host: str, port: int):
    """Test Qdrant connection."""
    import socket
    
    click.echo(f"🔍 Testing Qdrant connection to {host}:{port}")
    
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(5)
        result = sock.connect_ex((host, port))
        sock.close()
        
        if result == 0:
            click.echo("✅ Qdrant is reachable")
            
            # Try to make HTTP request
            try:
                import requests
                response = requests.get(f"http://{host}:{port}/collections", timeout=5)
                if response.status_code == 200:
                    click.echo("✅ Qdrant API is responding")
                    collections = response.json()
                    click.echo(f"📊 Collections: {len(collections.get('result', {}).get('collections', []))}")
                else:
                    click.echo(f"⚠️  Qdrant API returned status {response.status_code}")
            except ImportError:
                click.echo("⚠️  requests library not available for API test")
            except Exception as e:
                click.echo(f"⚠️  Qdrant API test failed: {e}")
        else:
            click.echo("❌ Qdrant is not reachable")
            
    except Exception as e:
        click.echo(f"❌ Connection test failed: {e}")


@cli.command()
@click.option('--host', default='localhost', help='Database host')
@click.option('--port', default=5432, help='PostgreSQL port')
def test_postgres(host: str, port: int):
    """Test PostgreSQL connection."""
    import socket
    
    click.echo(f"🔍 Testing PostgreSQL connection to {host}:{port}")
    
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(5)
        result = sock.connect_ex((host, port))
        sock.close()
        
        if result == 0:
            click.echo("✅ PostgreSQL is reachable")
        else:
            click.echo("❌ PostgreSQL is not reachable")
            
    except Exception as e:
        click.echo(f"❌ Connection test failed: {e}")


if __name__ == '__main__':
    cli()
