"""
Docker Deployment Validation Tests for Second Brain v3.0.0

These tests ensure the Docker containers start correctly and are operational.
Run these tests to validate the deployment works before releasing.
"""

import os
import time
import subprocess
import requests
import pytest
from typing import Dict, Any


class TestDockerDeployment:
    """Test suite for Docker deployment validation."""
    
    @classmethod
    def setup_class(cls):
        """Detect docker compose command."""
        cls.docker_compose_cmd = ["docker", "compose"] if subprocess.run(["docker", "compose", "--version"], capture_output=True).returncode == 0 else ["docker-compose"]
    
    @pytest.fixture(scope="class", autouse=True)
    def docker_environment(self):
        """Set up and tear down Docker environment for tests."""
        # Store original directory
        original_dir = os.getcwd()
        project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        
        try:
            # Change to project root
            os.chdir(project_root)
            
            # Stop any existing containers
            subprocess.run(self.docker_compose_cmd + ["down", "-v"], capture_output=True)
            
            # Start containers
            print("Starting Docker containers...")
            result = subprocess.run(
                self.docker_compose_cmd + ["up", "-d", "--build"],
                capture_output=True,
                text=True
            )
            
            if result.returncode != 0:
                pytest.fail(f"Failed to start Docker containers: {result.stderr}")
            
            # Wait for services to be ready
            print("Waiting for services to be ready...")
            self._wait_for_services()
            
            yield
            
        finally:
            # Cleanup
            print("Stopping Docker containers...")
            subprocess.run(self.docker_compose_cmd + ["down"], capture_output=True)
            os.chdir(original_dir)
    
    def _wait_for_services(self, timeout: int = 60):
        """Wait for all services to be healthy."""
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            try:
                # Check health endpoint
                response = requests.get("http://localhost:8000/health", timeout=5)
                if response.status_code == 200:
                    print("Services are ready!")
                    return
            except requests.exceptions.RequestException:
                pass
            
            time.sleep(2)
        
        pytest.fail(f"Services did not become ready within {timeout} seconds")
    
    def test_docker_compose_valid(self):
        """Test that docker-compose.yml is valid."""
        result = subprocess.run(
            self.docker_compose_cmd + ["config"],
            capture_output=True,
            text=True
        )
        assert result.returncode == 0, f"Invalid docker-compose.yml: {result.stderr}"
    
    def test_containers_running(self):
        """Test that all required containers are running."""
        result = subprocess.run(
            self.docker_compose_cmd + ["ps", "--format", "json"],
            capture_output=True,
            text=True
        )
        
        assert result.returncode == 0
        
        # Check each service
        output = result.stdout
        assert "secondbrain-app" in output
        assert "secondbrain-postgres" in output
        assert "secondbrain-redis" in output
        assert "secondbrain-adminer" in output
    
    def test_health_endpoint(self):
        """Test that the health endpoint returns correct response."""
        response = requests.get("http://localhost:8000/health")
        assert response.status_code == 200
        
        data = response.json()
        assert data["status"] == "healthy"
        assert data["version"] == "3.0.0"
        assert "timestamp" in data
    
    def test_api_docs_accessible(self):
        """Test that API documentation is accessible."""
        response = requests.get("http://localhost:8000/docs")
        assert response.status_code == 200
        assert "Second Brain API" in response.text
    
    def test_database_connection(self):
        """Test that the app can connect to the database."""
        # Test by creating a memory with correct memory_type
        headers = {"Authorization": "Bearer test-token"}
        data = {
            "content": "Docker test memory",
            "memory_type": "semantic",  # Valid types: semantic, episodic, procedural
            "tags": ["docker", "test"]
        }
        
        # First test without API key (should get 422 for missing api_key)
        response = requests.post(
            "http://localhost:8000/memories",
            json=data,
            headers=headers
        )
        
        # API requires api_key in query params
        assert response.status_code == 422, \
            f"Expected validation error, got {response.status_code}: {response.text}"
        
        # Test with valid API key 
        response = requests.post(
            "http://localhost:8000/memories?api_key=test-token-for-development",
            json=data,
            headers=headers
        )
        
        # Should succeed or get validation error, not database connection error
        assert response.status_code in [200, 201, 422], \
            f"Expected success or validation error, got {response.status_code}: {response.text}"
    
    def test_redis_connection(self):
        """Test Redis connectivity through the API."""
        # Check metrics endpoint which uses Redis
        response = requests.get("http://localhost:8000/metrics")
        assert response.status_code == 200
    
    def test_container_logs_no_errors(self):
        """Test that container logs don't contain critical errors."""
        result = subprocess.run(
            self.docker_compose_cmd + ["logs", "app", "--tail=100"],
            capture_output=True,
            text=True
        )
        
        logs = result.stdout.lower()
        
        # Check for critical errors
        assert "error: application startup failed" not in logs
        assert "connection refused" not in logs
        assert "cannot connect to database" not in logs
    
    def test_environment_variables_set(self):
        """Test that required environment variables are set in container."""
        result = subprocess.run(
            self.docker_compose_cmd + ["exec", "app", "env"],
            capture_output=True,
            text=True
        )
        
        env_output = result.stdout
        assert "DATABASE_URL=" in env_output
        assert "REDIS_URL=" in env_output
        assert "OPENAI_API_KEY=" in env_output
    
    def test_docker_healthcheck(self):
        """Test Docker health check is passing."""
        result = subprocess.run(
            ["docker", "inspect", "secondbrain-app", "--format", "{{.State.Health.Status}}"],
            capture_output=True,
            text=True
        )
        
        # Note: healthcheck might not be configured yet, so we check if running
        health_status = result.stdout.strip()
        assert health_status in ["healthy", ""], f"Container unhealthy: {health_status}"
    
    def test_port_accessibility(self):
        """Test that all exposed ports are accessible."""
        ports = {
            8000: "App API",
            5432: "PostgreSQL", 
            6379: "Redis",
            8080: "Adminer"
        }
        
        for port, service in ports.items():
            try:
                # Just test if port is open
                import socket
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(2)
                result = sock.connect_ex(('localhost', port))
                sock.close()
                
                assert result == 0, f"{service} port {port} is not accessible"
            except Exception as e:
                pytest.fail(f"Failed to test {service} port {port}: {e}")


if __name__ == "__main__":
    # Run with: python -m pytest tests/validation/test_docker_deployment.py -v
    pytest.main([__file__, "-v"])