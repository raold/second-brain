"""
Test the HealthService implementation
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime

from app.services.health_service import HealthService


class TestHealthService:
    """Test HealthService functionality"""
    
    def setup_method(self):
        """Setup test fixtures"""
        self.mock_db = AsyncMock()
        self.health_service = HealthService(self.mock_db)
    
    @pytest.mark.asyncio
    async def test_get_health_status_healthy(self):
        """Test health status when system is healthy"""
        health_status = await self.health_service.get_health_status()
        
        assert health_status["status"] == "healthy"
        assert health_status["timestamp"] is not None
        assert health_status["version"] is not None
        assert "uptime_seconds" in health_status
        assert health_status["environment"] is not None
    
    @pytest.mark.asyncio
    async def test_get_health_status_with_exception(self):
        """Test health status when an exception occurs"""
        # Mock version_info to raise exception
        with patch('app.services.health_service.get_version_info') as mock_version:
            mock_version.side_effect = Exception("Version error")
            
            health_status = await self.health_service.get_health_status()
            
            assert health_status["status"] == "unhealthy"
            assert "error" in health_status
            assert "Version error" in health_status["error"]
    
    @pytest.mark.asyncio
    async def test_get_system_status(self):
        """Test system status information"""
        system_status = await self.health_service.get_system_status()
        
        assert "cpu" in system_status
        assert "memory" in system_status
        assert "disk" in system_status
        assert "database" in system_status
        assert "recommendations" in system_status
        
        # Check CPU info structure
        assert "percent" in system_status["cpu"]
        assert "count" in system_status["cpu"]
        
        # Check memory info structure
        assert "total" in system_status["memory"]
        assert "available" in system_status["memory"]
        assert "percent" in system_status["memory"]
    
    @pytest.mark.asyncio
    async def test_get_performance_metrics(self):
        """Test performance metrics collection"""
        metrics = await self.health_service.get_performance_metrics()
        
        assert "system" in metrics
        assert "database" in metrics
        assert "response_times" in metrics
        
        # Check system metrics
        assert "cpu_usage" in metrics["system"]
        assert "memory_usage" in metrics["system"]
        assert "disk_usage" in metrics["system"]
        
        # Check response times
        assert "health_check" in metrics["response_times"]
    
    @pytest.mark.asyncio
    async def test_run_diagnostics(self):
        """Test diagnostics execution"""
        diagnostics = await self.health_service.run_diagnostics()
        
        assert "overall_status" in diagnostics
        assert "checks" in diagnostics
        assert "summary" in diagnostics
        assert "timestamp" in diagnostics
        
        # Should have multiple diagnostic checks
        assert len(diagnostics["checks"]) > 0
        
        # Each check should have required fields
        for check in diagnostics["checks"]:
            assert "name" in check
            assert "status" in check
            assert "message" in check
    
    @pytest.mark.asyncio
    async def test_health_check_with_real_timestamp(self):
        """Test that health check includes proper timestamp"""
        before_check = datetime.utcnow()
        health_status = await self.health_service.get_health_status()
        after_check = datetime.utcnow()
        
        # Parse timestamp and verify it's within reasonable range
        timestamp = datetime.fromisoformat(health_status["timestamp"])
        assert before_check <= timestamp <= after_check
    
    @pytest.mark.asyncio
    async def test_service_uptime_tracking(self):
        """Test that service tracks uptime correctly"""
        # Get initial status
        status1 = await self.health_service.get_health_status()
        initial_uptime = status1["uptime_seconds"]
        
        # Should have some uptime (even if very small)
        assert initial_uptime >= 0
        
        # Create new service instance (simulating restart)
        new_service = HealthService(self.mock_db)
        status2 = await new_service.get_health_status()
        new_uptime = status2["uptime_seconds"]
        
        # New service should have minimal uptime
        assert new_uptime < initial_uptime or new_uptime == 0


class TestHealthServiceIntegration:
    """Integration tests for HealthService"""
    
    @pytest.mark.asyncio
    async def test_health_service_with_database(self):
        """Test health service with database integration"""
        mock_db = AsyncMock()
        
        # Mock database methods that might be called
        mock_db.get_memory_count = AsyncMock(return_value=100)
        mock_db.get_database_size = AsyncMock(return_value=1024 * 1024)
        mock_db.check_connection = AsyncMock(return_value=True)
        
        health_service = HealthService(mock_db)
        
        # Test all major methods work with database
        health_status = await health_service.get_health_status()
        system_status = await health_service.get_system_status()
        performance = await health_service.get_performance_metrics()
        diagnostics = await health_service.run_diagnostics()
        
        assert health_status["status"] == "healthy"
        assert "database" in system_status
        assert "database" in performance
        assert diagnostics["overall_status"] in ["healthy", "degraded", "unhealthy"]
    
    @pytest.mark.asyncio
    async def test_health_service_without_database(self):
        """Test health service without database"""
        health_service = HealthService(None)
        
        # Should still work without database
        health_status = await health_service.get_health_status()
        system_status = await health_service.get_system_status()
        
        assert health_status["status"] == "healthy"
        assert isinstance(system_status, dict)
    
    @pytest.mark.asyncio
    async def test_multiple_health_checks_consistency(self):
        """Test that multiple health checks are consistent"""
        mock_db = AsyncMock()
        health_service = HealthService(mock_db)
        
        # Run multiple health checks
        health1 = await health_service.get_health_status()
        health2 = await health_service.get_health_status()
        
        # Status should be consistent
        assert health1["status"] == health2["status"]
        assert health1["version"] == health2["version"]
        assert health1["environment"] == health2["environment"]
        
        # Uptime should increase slightly
        assert health2["uptime_seconds"] >= health1["uptime_seconds"]


class TestHealthServiceErrorHandling:
    """Test error handling in HealthService"""
    
    @pytest.mark.asyncio
    async def test_database_error_handling(self):
        """Test that database errors are handled gracefully"""
        mock_db = AsyncMock()
        
        # Mock database methods that raise exceptions
        mock_db.get_memory_count = AsyncMock(side_effect=Exception("DB error"))
        mock_db.check_connection = AsyncMock(side_effect=Exception("Connection failed"))
        
        health_service = HealthService(mock_db)
        
        # Should handle errors gracefully and not crash
        system_status = await health_service.get_system_status()
        performance = await health_service.get_performance_metrics()
        diagnostics = await health_service.run_diagnostics()
        
        # Should return valid structures even with errors
        assert isinstance(system_status, dict)
        assert isinstance(performance, dict)
        assert isinstance(diagnostics, dict)
        
        # Database status should indicate issues
        if "database" in system_status:
            assert "error" in system_status["database"] or system_status["database"]["status"] == "unhealthy"
    
    @pytest.mark.asyncio
    async def test_system_resource_error_handling(self):
        """Test handling of system resource access errors"""
        # Mock psutil to raise exceptions
        with patch('psutil.cpu_percent') as mock_cpu:
            mock_cpu.side_effect = Exception("CPU access error")
            
            health_service = HealthService()
            
            # Should handle psutil errors gracefully
            system_status = await health_service.get_system_status()
            
            assert isinstance(system_status, dict)
            # Should still have some system info even if CPU fails
            assert "memory" in system_status or "disk" in system_status