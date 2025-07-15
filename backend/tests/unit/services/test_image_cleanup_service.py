"""
Tests for image_cleanup_service.py
"""
import pytest
import os
import tempfile
import shutil
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path
from sqlalchemy.orm import Session

from services.image_cleanup_service import (
    ImageCleanupService, 
    image_cleanup_service,
    scheduled_image_cleanup,
    cleanup_images_sync,
    DeletionResult,
    CleanupResult
)
from models.product import Image


class TestImageCleanupService:
    """Test ImageCleanupService class"""
    
    def test_init_default_image_dir(self):
        """Test initialization with default image directory"""
        service = ImageCleanupService()
        assert service.image_dir == Path("./images")
    
    def test_init_custom_image_dir(self):
        """Test initialization with custom image directory"""
        custom_dir = "/custom/images"
        service = ImageCleanupService(custom_dir)
        assert service.image_dir == Path(custom_dir)
    
    def test_get_database_image_files_success(self):
        """Test successful retrieval of database image files"""
        service = ImageCleanupService()
        mock_db = Mock(spec=Session)
        
        # Mock query results
        mock_query = Mock()
        mock_db.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.all.return_value = [
            ("image1.jpg",),
            ("image2.png",),
            ("http://example.com/image3.jpg",),  # Should be filtered out
            ("https://example.com/image4.png",), # Should be filtered out
            ("image5.webp",),
            (None,),  # Should be filtered out
        ]
        
        result = service.get_database_image_files(mock_db)
        
        # Verify only local file IDs are returned
        expected = {"image1.jpg", "image2.png", "image5.webp"}
        assert result == expected
        
        # Verify query was called correctly
        mock_db.query.assert_called_once_with(Image.url)
        mock_query.filter.assert_called_once()
        mock_query.all.assert_called_once()
    
    def test_get_database_image_files_exception(self):
        """Test database image files retrieval with exception"""
        service = ImageCleanupService()
        mock_db = Mock(spec=Session)
        mock_db.query.side_effect = Exception("Database error")
        
        result = service.get_database_image_files(mock_db)
        
        assert result == set()
    
    def test_get_filesystem_image_files_success(self):
        """Test successful retrieval of filesystem image files"""
        with tempfile.TemporaryDirectory() as temp_dir:
            service = ImageCleanupService(temp_dir)
            
            # Create test files
            image_files = [
                "test1.jpg",
                "test2.png", 
                "test3.gif",
                "test4.webp",
                "test5.bmp",
                "test6.JPEG",  # Test case insensitive
                "readme.txt",   # Should be filtered out
                "config.json"   # Should be filtered out
            ]
            
            for filename in image_files:
                Path(temp_dir, filename).touch()
            
            result = service.get_filesystem_image_files()
            
            # Verify only image files are returned
            expected = {"test1.jpg", "test2.png", "test3.gif", "test4.webp", "test5.bmp", "test6.JPEG"}
            assert result == expected
    
    def test_get_filesystem_image_files_no_directory(self):
        """Test filesystem image files retrieval when directory doesn't exist"""
        service = ImageCleanupService("/nonexistent/path")
        
        result = service.get_filesystem_image_files()
        
        assert result == set()
    
    def test_get_filesystem_image_files_exception(self):
        """Test filesystem image files retrieval with exception"""
        service = ImageCleanupService()
        
        with patch('pathlib.Path.exists', return_value=True), \
             patch('pathlib.Path.iterdir', side_effect=Exception("IO Error")):
            
            result = service.get_filesystem_image_files()
            
            assert result == set()
    
    def test_find_orphaned_images_success(self):
        """Test finding orphaned images"""
        service = ImageCleanupService()
        mock_db = Mock(spec=Session)
        
        with patch.object(service, 'get_database_image_files', return_value={"db1.jpg", "db2.png"}), \
             patch.object(service, 'get_filesystem_image_files', return_value={"db1.jpg", "db2.png", "orphan1.jpg", "orphan2.png"}):
            
            result = service.find_orphaned_images(mock_db)
            
            assert set(result) == {"orphan1.jpg", "orphan2.png"}
    
    def test_find_orphaned_images_no_orphans(self):
        """Test finding orphaned images when none exist"""
        service = ImageCleanupService()
        mock_db = Mock(spec=Session)
        
        with patch.object(service, 'get_database_image_files', return_value={"db1.jpg", "db2.png"}), \
             patch.object(service, 'get_filesystem_image_files', return_value={"db1.jpg", "db2.png"}):
            
            result = service.find_orphaned_images(mock_db)
            
            assert result == []
    
    def test_delete_orphaned_images_dry_run(self):
        """Test deleting orphaned images in dry run mode"""
        with tempfile.TemporaryDirectory() as temp_dir:
            service = ImageCleanupService(temp_dir)
            
            # Create test files
            test_files = ["orphan1.jpg", "orphan2.png"]
            for filename in test_files:
                file_path = Path(temp_dir, filename)
                file_path.write_text("test content")
            
            result = service.delete_orphaned_images(test_files, dry_run=True)
            
            # Verify dry run results
            assert result['deleted_count'] == 2
            assert result['failed_count'] == 0
            assert result['total_size_freed'] > 0
            assert set(result['deleted_files']) == set(test_files)
            assert result['failed_files'] == []
            
            # Verify files still exist (dry run)
            for filename in test_files:
                assert Path(temp_dir, filename).exists()
    
    def test_delete_orphaned_images_actual_deletion(self):
        """Test actual deletion of orphaned images"""
        with tempfile.TemporaryDirectory() as temp_dir:
            service = ImageCleanupService(temp_dir)
            
            # Create test files
            test_files = ["orphan1.jpg", "orphan2.png"]
            for filename in test_files:
                file_path = Path(temp_dir, filename)
                file_path.write_text("test content")
            
            result = service.delete_orphaned_images(test_files, dry_run=False)
            
            # Verify actual deletion results
            assert result['deleted_count'] == 2
            assert result['failed_count'] == 0
            assert result['total_size_freed'] > 0
            assert set(result['deleted_files']) == set(test_files)
            assert result['failed_files'] == []
            
            # Verify files were actually deleted
            for filename in test_files:
                assert not Path(temp_dir, filename).exists()
    
    def test_delete_orphaned_images_empty_list(self):
        """Test deleting orphaned images with empty list"""
        service = ImageCleanupService()
        
        result = service.delete_orphaned_images([], dry_run=False)
        
        # Verify empty result
        assert result['deleted_count'] == 0
        assert result['failed_count'] == 0
        assert result['total_size_freed'] == 0
        assert result['deleted_files'] == []
        assert result['failed_files'] == []
    
    def test_delete_orphaned_images_missing_files(self):
        """Test deleting orphaned images when files don't exist"""
        service = ImageCleanupService()
        
        test_files = ["nonexistent1.jpg", "nonexistent2.png"]
        result = service.delete_orphaned_images(test_files, dry_run=False)
        
        # Verify no files were processed
        assert result['deleted_count'] == 0
        assert result['failed_count'] == 0
        assert result['total_size_freed'] == 0
        assert result['deleted_files'] == []
        assert result['failed_files'] == []
    
    def test_delete_orphaned_images_with_failures(self):
        """Test deleting orphaned images with some failures"""
        with tempfile.TemporaryDirectory() as temp_dir:
            service = ImageCleanupService(temp_dir)
            
            # Create test files
            test_files = ["orphan1.jpg", "orphan2.png", "orphan3.gif"]
            for filename in test_files:
                file_path = Path(temp_dir, filename)
                file_path.write_text("test content")
            
            # Mock unlink to fail for second file
            original_unlink = Path.unlink
            def mock_unlink(self):
                if self.name == "orphan2.png":
                    raise PermissionError("Permission denied")
                return original_unlink(self)
            
            with patch.object(Path, 'unlink', mock_unlink):
                result = service.delete_orphaned_images(test_files, dry_run=False)
            
            # Verify mixed results
            assert result['deleted_count'] == 2
            assert result['failed_count'] == 1
            assert result['total_size_freed'] > 0
            assert set(result['deleted_files']) == {"orphan1.jpg", "orphan3.gif"}
            assert result['failed_files'] == ["orphan2.png"]
    
    def test_cleanup_orphaned_images_success(self):
        """Test complete cleanup process success"""
        service = ImageCleanupService()
        
        with patch('services.image_cleanup_service.get_db') as mock_get_db, \
             patch.object(service, 'find_orphaned_images', return_value=["orphan1.jpg", "orphan2.png"]) as mock_find, \
             patch.object(service, 'delete_orphaned_images') as mock_delete:
            
            # Setup mocks
            mock_db = Mock()
            mock_get_db.return_value = iter([mock_db])
            mock_delete.return_value = {
                'deleted_count': 2,
                'failed_count': 0,
                'total_size_freed': 1024,
                'deleted_files': ["orphan1.jpg", "orphan2.png"],
                'failed_files': []
            }
            
            result = service.cleanup_orphaned_images(dry_run=True)
            
            # Verify successful cleanup
            assert result['success'] is True
            assert result['deleted_count'] == 2
            assert result['failed_count'] == 0
            assert result['total_size_freed'] == 1024
            assert result['deleted_files'] == ["orphan1.jpg", "orphan2.png"]
            assert result['failed_files'] == []
            assert result['message'] == "Cleanup completed successfully"
            
            # Verify methods were called
            mock_find.assert_called_once_with(mock_db)
            mock_delete.assert_called_once_with(["orphan1.jpg", "orphan2.png"], dry_run=True)
            mock_db.close.assert_called_once()
    
    def test_cleanup_orphaned_images_exception(self):
        """Test cleanup process with exception"""
        service = ImageCleanupService()
        
        with patch('services.image_cleanup_service.get_db', side_effect=Exception("Database error")):
            
            result = service.cleanup_orphaned_images(dry_run=True)
            
            # Verify error result
            assert result['success'] is False
            assert "Cleanup failed: Database error" in result['message']
            assert result['deleted_count'] == 0
            assert result['failed_count'] == 0
            assert result['total_size_freed'] == 0
            assert result['deleted_files'] == []
            assert result['failed_files'] == []
    
    def test_cleanup_orphaned_images_db_closes_on_exception(self):
        """Test cleanup process ensures database session is closed on exception"""
        service = ImageCleanupService()
        
        with patch('services.image_cleanup_service.get_db') as mock_get_db, \
             patch.object(service, 'find_orphaned_images', side_effect=Exception("Find error")):
            
            # Setup mocks
            mock_db = Mock()
            mock_get_db.return_value = iter([mock_db])
            
            result = service.cleanup_orphaned_images(dry_run=True)
            
            # Verify database was closed even on exception
            mock_db.close.assert_called_once()
            assert result['success'] is False


class TestGlobalFunctions:
    """Test global functions and service instance"""
    
    def test_global_service_instance(self):
        """Test global service instance exists"""
        assert image_cleanup_service is not None
        assert isinstance(image_cleanup_service, ImageCleanupService)
    
    @pytest.mark.asyncio
    async def test_scheduled_image_cleanup_single_iteration(self):
        """Test scheduled cleanup single iteration"""
        with patch.object(image_cleanup_service, 'cleanup_orphaned_images') as mock_cleanup, \
             patch('asyncio.sleep') as mock_sleep:
            
            # Setup mock to return success then raise exception to break loop
            mock_cleanup.side_effect = [
                {'success': True, 'deleted_count': 1},
                KeyboardInterrupt()  # Break the loop
            ]
            
            # Run scheduled cleanup
            with pytest.raises(KeyboardInterrupt):
                await scheduled_image_cleanup(interval_hours=1, dry_run=True)
            
            # Verify cleanup was called
            assert mock_cleanup.call_count == 2
            mock_cleanup.assert_called_with(dry_run=True)
            mock_sleep.assert_called_once_with(3600)  # 1 hour in seconds
    
    @pytest.mark.asyncio
    async def test_scheduled_image_cleanup_failure(self):
        """Test scheduled cleanup with failure"""
        with patch.object(image_cleanup_service, 'cleanup_orphaned_images') as mock_cleanup, \
             patch('asyncio.sleep') as mock_sleep:
            
            # Setup mock to return failure then raise exception to break loop
            mock_cleanup.side_effect = [
                {'success': False, 'message': 'Cleanup failed'},
                KeyboardInterrupt()  # Break the loop
            ]
            
            # Run scheduled cleanup
            with pytest.raises(KeyboardInterrupt):
                await scheduled_image_cleanup(interval_hours=24, dry_run=False)
            
            # Verify cleanup was called
            assert mock_cleanup.call_count == 2
            mock_cleanup.assert_called_with(dry_run=False)
            mock_sleep.assert_called_once_with(86400)  # 24 hours in seconds
    
    @pytest.mark.asyncio
    async def test_scheduled_image_cleanup_exception(self):
        """Test scheduled cleanup with exception"""
        with patch.object(image_cleanup_service, 'cleanup_orphaned_images', side_effect=Exception("Service error")), \
             patch('asyncio.sleep') as mock_sleep:
            
            # Setup mock to raise exception twice then break loop
            mock_sleep.side_effect = [None, KeyboardInterrupt()]
            
            # Run scheduled cleanup
            with pytest.raises(KeyboardInterrupt):
                await scheduled_image_cleanup(interval_hours=1, dry_run=True)
            
            # Verify sleep was called twice (after each exception)
            assert mock_sleep.call_count == 2
    
    def test_cleanup_images_sync(self):
        """Test synchronous cleanup wrapper"""
        with patch.object(image_cleanup_service, 'cleanup_orphaned_images') as mock_cleanup:
            mock_cleanup.return_value = {
                'success': True,
                'deleted_count': 3,
                'failed_count': 0,
                'total_size_freed': 2048,
                'deleted_files': ["test1.jpg", "test2.png", "test3.gif"],
                'failed_files': [],
                'message': "Cleanup completed successfully"
            }
            
            result = cleanup_images_sync(dry_run=False)
            
            # Verify result
            assert result['success'] is True
            assert result['deleted_count'] == 3
            assert result['failed_count'] == 0
            assert result['total_size_freed'] == 2048
            assert result['deleted_files'] == ["test1.jpg", "test2.png", "test3.gif"]
            assert result['failed_files'] == []
            assert result['message'] == "Cleanup completed successfully"
            
            # Verify service method was called
            mock_cleanup.assert_called_once_with(dry_run=False)
    
    def test_cleanup_images_sync_default_dry_run(self):
        """Test synchronous cleanup wrapper with default dry_run"""
        with patch.object(image_cleanup_service, 'cleanup_orphaned_images') as mock_cleanup:
            mock_cleanup.return_value = {
                'success': True,
                'deleted_count': 0,
                'failed_count': 0,
                'total_size_freed': 0,
                'deleted_files': [],
                'failed_files': [],
                'message': "Cleanup completed successfully"
            }
            
            result = cleanup_images_sync()
            
            # Verify service method was called with default dry_run=True
            mock_cleanup.assert_called_once_with(dry_run=True)