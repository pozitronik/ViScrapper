"""
Comprehensive unit tests for maintenance API router.

This module contains tests for maintenance endpoints including
orphaned image cleanup and image statistics.
"""

import pytest
from unittest.mock import Mock, patch
from fastapi.testclient import TestClient
from fastapi import FastAPI
from pathlib import Path

from api.routers.maintenance import router
from database.session import get_db


@pytest.fixture
def test_app():
    """Create test FastAPI app with maintenance router."""
    app = FastAPI()
    app.include_router(router)
    return app


@pytest.fixture
def mock_db():
    """Create mock database session."""
    return Mock()


@pytest.fixture
def test_client(test_app, mock_db):
    """Create test client with mocked database dependency."""
    def mock_get_db():
        return mock_db
    
    test_app.dependency_overrides[get_db] = mock_get_db
    client = TestClient(test_app)
    yield client
    test_app.dependency_overrides.clear()


class TestMaintenanceRouter:
    """Test suite for maintenance API router."""

    @patch('api.routers.maintenance.image_cleanup_service')
    def test_cleanup_orphaned_images_dry_run(self, mock_cleanup_service, test_client):
        """Test orphaned image cleanup in dry run mode."""
        mock_cleanup_results = {
            'deleted_count': 5,
            'failed_count': 0,
            'total_size_freed': 1024000,
            'deleted_files': ['image1.jpg', 'image2.png'],
            'failed_files': [],
            'success': True,
            'message': 'Cleanup completed'
        }
        mock_cleanup_service.cleanup_orphaned_images.return_value = mock_cleanup_results
        
        response = test_client.post("/api/v1/maintenance/cleanup-orphaned-images?dry_run=true")
        
        assert response.status_code == 200
        data = response.json()
        assert data["data"]["deleted_count"] == 5
        assert data["data"]["total_size_freed"] == 1024000
        assert "Would delete 5 orphaned images" in data["message"]
        
        mock_cleanup_service.cleanup_orphaned_images.assert_called_once_with(dry_run=True)

    @patch('api.routers.maintenance.image_cleanup_service')
    def test_cleanup_orphaned_images_actual_cleanup(self, mock_cleanup_service, test_client):
        """Test actual orphaned image cleanup."""
        mock_cleanup_results = {
            'deleted_count': 3,
            'failed_count': 1,
            'total_size_freed': 512000,
            'deleted_files': ['image1.jpg', 'image2.png', 'image3.gif'],
            'failed_files': ['locked_image.jpg'],
            'success': True,
            'message': 'Cleanup completed'
        }
        mock_cleanup_service.cleanup_orphaned_images.return_value = mock_cleanup_results
        
        response = test_client.post("/api/v1/maintenance/cleanup-orphaned-images?dry_run=false")
        
        assert response.status_code == 200
        data = response.json()
        assert data["data"]["deleted_count"] == 3
        assert data["data"]["failed_count"] == 1
        assert "Deleted 3 orphaned images" in data["message"]
        assert "1 files failed to delete" in data["message"]
        
        mock_cleanup_service.cleanup_orphaned_images.assert_called_once_with(dry_run=False)

    @patch('api.routers.maintenance.image_cleanup_service')
    def test_cleanup_orphaned_images_no_orphans(self, mock_cleanup_service, test_client):
        """Test cleanup when no orphaned images exist."""
        mock_cleanup_results = {
            'deleted_count': 0,
            'failed_count': 0,
            'total_size_freed': 0,
            'deleted_files': [],
            'failed_files': [],
            'success': True,
            'message': 'Cleanup completed'
        }
        mock_cleanup_service.cleanup_orphaned_images.return_value = mock_cleanup_results
        
        response = test_client.post("/api/v1/maintenance/cleanup-orphaned-images")
        
        assert response.status_code == 200
        data = response.json()
        assert data["data"]["deleted_count"] == 0
        assert "Would delete 0 orphaned images" in data["message"]

    @patch('api.routers.maintenance.image_cleanup_service')
    def test_get_image_statistics_success(self, mock_cleanup_service, test_client):
        """Test successful image statistics retrieval."""
        # Mock service methods
        mock_cleanup_service.get_database_image_files.return_value = [
            'db_image1.jpg', 'db_image2.png', 'db_image3.gif'
        ]
        mock_cleanup_service.get_filesystem_image_files.return_value = [
            'db_image1.jpg', 'db_image2.png', 'orphan1.jpg', 'orphan2.png'
        ]
        mock_cleanup_service.find_orphaned_images.return_value = [
            'orphan1.jpg', 'orphan2.png'
        ]
        
        # Mock image directory and file stats
        mock_image_dir = Mock()
        mock_cleanup_service.image_dir = mock_image_dir
        
        # Mock file paths and their sizes
        mock_files = {
            'db_image1.jpg': 100000,
            'db_image2.png': 200000,
            'orphan1.jpg': 50000,
            'orphan2.png': 75000
        }
        
        def mock_file_path(filename):
            mock_path = Mock()
            mock_path.exists.return_value = True
            mock_stat = Mock()
            mock_stat.st_size = mock_files.get(filename, 0)
            mock_path.stat.return_value = mock_stat
            return mock_path
        
        mock_image_dir.__truediv__ = lambda self, other: mock_file_path(other)
        
        response = test_client.get("/api/v1/maintenance/image-statistics")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["data"]["database_images"] == 3
        assert data["data"]["filesystem_images"] == 4
        assert data["data"]["orphaned_images"] == 2
        assert data["data"]["total_filesystem_size_bytes"] == 425000
        assert data["data"]["orphaned_size_bytes"] == 125000
        assert data["data"]["total_filesystem_size_mb"] == 0.41
        assert data["data"]["orphaned_size_mb"] == 0.12
        assert data["data"]["storage_efficiency_percent"] == 70.59
        assert data["message"] == "Image statistics retrieved successfully"

    @patch('api.routers.maintenance.image_cleanup_service')
    def test_get_image_statistics_empty_directory(self, mock_cleanup_service, test_client):
        """Test image statistics when directory is empty."""
        # Mock empty results
        mock_cleanup_service.get_database_image_files.return_value = []
        mock_cleanup_service.get_filesystem_image_files.return_value = []
        mock_cleanup_service.find_orphaned_images.return_value = []
        mock_cleanup_service.image_dir = Path("/empty/dir")
        
        response = test_client.get("/api/v1/maintenance/image-statistics")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["data"]["database_images"] == 0
        assert data["data"]["filesystem_images"] == 0
        assert data["data"]["orphaned_images"] == 0
        assert data["data"]["total_filesystem_size_bytes"] == 0
        assert data["data"]["storage_efficiency_percent"] == 100

    @patch('api.routers.maintenance.image_cleanup_service')
    def test_get_image_statistics_file_access_error(self, mock_cleanup_service, test_client):
        """Test image statistics when file access fails."""
        # Mock service methods to raise exception
        mock_cleanup_service.get_database_image_files.side_effect = Exception("Database error")
        
        # The endpoint should re-raise the exception which results in 500
        with pytest.raises(Exception, match="Database error"):
            response = test_client.get("/api/v1/maintenance/image-statistics")

    @patch('api.routers.maintenance.image_cleanup_service')
    def test_get_image_statistics_missing_files(self, mock_cleanup_service, test_client):
        """Test image statistics with some missing files."""
        mock_cleanup_service.get_database_image_files.return_value = ['existing.jpg']
        mock_cleanup_service.get_filesystem_image_files.return_value = ['existing.jpg', 'missing.jpg']
        mock_cleanup_service.find_orphaned_images.return_value = ['missing.jpg']
        
        mock_image_dir = Mock()
        mock_cleanup_service.image_dir = mock_image_dir
        
        def mock_file_path(filename):
            mock_path = Mock()
            # Only 'existing.jpg' exists
            mock_path.exists.return_value = filename == 'existing.jpg'
            if filename == 'existing.jpg':
                mock_stat = Mock()
                mock_stat.st_size = 100000
                mock_path.stat.return_value = mock_stat
            return mock_path
        
        mock_image_dir.__truediv__ = lambda self, other: mock_file_path(other)
        
        response = test_client.get("/api/v1/maintenance/image-statistics")
        
        assert response.status_code == 200
        data = response.json()
        
        # Only the existing file should be counted in size calculations
        assert data["data"]["total_filesystem_size_bytes"] == 100000
        assert data["data"]["orphaned_size_bytes"] == 0  # missing.jpg doesn't exist


class TestMaintenanceRouterErrorHandling:
    """Test error handling in maintenance router."""

    def test_invalid_dry_run_parameter(self, test_client):
        """Test invalid dry_run parameter."""
        response = test_client.post("/api/v1/maintenance/cleanup-orphaned-images?dry_run=invalid")
        assert response.status_code == 422  # Validation error

    @patch('api.routers.maintenance.image_cleanup_service')
    def test_cleanup_service_exception(self, mock_cleanup_service, test_client):
        """Test cleanup when service raises an exception."""
        mock_cleanup_service.cleanup_orphaned_images.side_effect = Exception("Service unavailable")
        
        # The endpoint should re-raise the exception
        with pytest.raises(Exception, match="Service unavailable"):
            response = test_client.post("/api/v1/maintenance/cleanup-orphaned-images")