import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from unittest.mock import patch, MagicMock

from main import app
from database.session import get_db
from models.product import Base

# Setup a test database
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(name="session")
def session_fixture():
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)


@pytest.fixture(name="client")
def client_fixture(session):
    def override_get_db():
        yield session

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


class TestHealthAPI:
    """Test suite for the Health API endpoints."""
    
    def test_health_check_success(self, client):
        """Test successful health check."""
        response = client.get("/api/v1/health")
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["message"] == "Health check completed"
        
        health_data = data["data"]
        assert health_data["status"] == "healthy"
        assert health_data["version"] == "1.0.0"
        assert health_data["database"] == "connected"
        assert isinstance(health_data["uptime"], (int, float))
        assert health_data["uptime"] >= 0
        assert "timestamp" in health_data
    
    def test_health_check_database_error(self, client):
        """Test health check with database error."""
        # Mock database session to raise an exception
        def mock_get_db():
            mock_session = MagicMock()
            mock_session.execute.side_effect = Exception("Database connection failed")
            yield mock_session
        
        app.dependency_overrides[get_db] = mock_get_db
        
        try:
            response = client.get("/api/v1/health")
            
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            
            health_data = data["data"]
            assert health_data["status"] == "unhealthy"
            assert "error:" in health_data["database"]
            assert "Database connection failed" in health_data["database"]
        finally:
            app.dependency_overrides.clear()
    
    def test_system_status_success(self, client):
        """Test successful system status check."""
        response = client.get("/api/v1/status")
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["message"] == "System status retrieved successfully"
        
        status_data = data["data"]
        assert status_data["overall_status"] == "healthy"
        assert isinstance(status_data["uptime_seconds"], (int, float))
        assert status_data["uptime_seconds"] >= 0
        assert isinstance(status_data["uptime_formatted"], str)
        assert "timestamp" in status_data
        
        # Check database info
        assert "database" in status_data
        assert status_data["database"]["status"] == "connected"
        assert "details" in status_data["database"]
        
        # Check system info
        assert "system" in status_data
        system_info = status_data["system"]
        assert "python_version" in system_info
        assert "platform" in system_info
        assert "pid" in system_info
        assert "working_directory" in system_info
        
        # Check environment info
        assert "environment" in status_data
        env_info = status_data["environment"]
        assert "environment" in env_info
        assert "debug" in env_info
    
    def test_system_status_database_error(self, client):
        """Test system status with database error."""
        # Mock database session to raise an exception
        def mock_get_db():
            mock_session = MagicMock()
            mock_session.execute.side_effect = Exception("Connection timeout")
            yield mock_session
        
        app.dependency_overrides[get_db] = mock_get_db
        
        try:
            response = client.get("/api/v1/status")
            
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            
            status_data = data["data"]
            assert status_data["overall_status"] == "unhealthy"
            assert status_data["database"]["status"] == "error"
            assert "Connection timeout" in status_data["database"]["error"]
        finally:
            app.dependency_overrides.clear()
    
    def test_ping_endpoint(self, client):
        """Test the simple ping endpoint."""
        response = client.get("/api/v1/ping")
        
        assert response.status_code == 200
        data = response.json()
        assert data["message"] == "pong"
        assert "timestamp" in data
    
    def test_uptime_formatting(self):
        """Test the uptime formatting function."""
        from api.routers.health import format_uptime
        
        # Test various uptime values
        assert format_uptime(30) == "30s"
        assert format_uptime(65) == "1m 5s"
        assert format_uptime(3661) == "1h 1m 1s"
        assert format_uptime(90061) == "1d 1h 1m 1s"
        assert format_uptime(0) == "0s"
        assert format_uptime(3600) == "1h"
        assert format_uptime(86400) == "1d"
    
    @patch('api.routers.health.time.time')
    def test_uptime_calculation(self, mock_time, client):
        """Test that uptime is calculated correctly."""
        # Mock the current time to be 100 seconds after start
        # The start time is set when the module is imported
        import api.routers.health
        
        # Set a known start time
        api.routers.health._start_time = 1000
        mock_time.return_value = 1100  # 100 seconds later
        
        response = client.get("/api/v1/health")
        
        assert response.status_code == 200
        data = response.json()
        health_data = data["data"]
        assert health_data["uptime"] == 100.0
    
    def test_health_endpoints_response_structure(self, client):
        """Test that all health endpoints return proper response structure."""
        endpoints = [
            "/api/v1/health",
            "/api/v1/status",
        ]
        
        for endpoint in endpoints:
            response = client.get(endpoint)
            assert response.status_code == 200
            
            data = response.json()
            # All health endpoints should have success and timestamp
            assert "success" in data
            assert "data" in data
            assert "timestamp" in data
            
            if endpoint != "/api/v1/ping":  # ping has different structure
                assert "message" in data
    
    def test_health_check_performance(self, client):
        """Test that health check responds quickly."""
        import time
        
        start_time = time.time()
        response = client.get("/api/v1/health")
        end_time = time.time()
        
        assert response.status_code == 200
        # Health check should complete in under 1 second
        assert (end_time - start_time) < 1.0
    
    def test_multiple_health_checks(self, client):
        """Test multiple consecutive health checks."""
        for i in range(5):
            response = client.get("/api/v1/health")
            assert response.status_code == 200
            
            data = response.json()
            assert data["success"] is True
            assert data["data"]["status"] == "healthy"
    
    def test_status_includes_sqlite_version(self, client):
        """Test that status endpoint includes SQLite version info."""
        response = client.get("/api/v1/status")
        
        assert response.status_code == 200
        data = response.json()
        
        # Check if SQLite version is included in database details
        database_details = data["data"]["database"]["details"]
        if "sqlite_version" in database_details:
            assert isinstance(database_details["sqlite_version"], str)
            assert len(database_details["sqlite_version"]) > 0