"""
Comprehensive unit tests for backup service.

This module contains extensive tests for all backup service functionality including
BackupConfig, BackupInfo, and DatabaseBackupService classes with all their methods.
"""

import pytest
import asyncio
import os
import tempfile
import sqlite3
import gzip
from unittest.mock import Mock, patch, MagicMock, AsyncMock, mock_open
from datetime import datetime
from pathlib import Path

from services.backup_service import (
    BackupConfig,
    BackupInfo,
    DatabaseBackupService
)


class TestBackupConfig:
    """Test suite for BackupConfig class."""

    def test_backup_config_default_values(self):
        """Test BackupConfig initialization with default values."""
        config = BackupConfig()
        
        assert config.source_db_path == "viparser.db"
        assert config.backup_dir == Path("backups")
        assert config.max_backups == 10
        assert config.backup_interval_hours == 24
        assert config.compression is True
        assert config.verify_backups is True

    def test_backup_config_custom_values(self):
        """Test BackupConfig initialization with custom values."""
        config = BackupConfig(
            source_db_path="custom.db",
            backup_dir="custom_backups",
            max_backups=5,
            backup_interval_hours=12,
            compression=False,
            verify_backups=False
        )
        
        assert config.source_db_path == "custom.db"
        assert config.backup_dir == Path("custom_backups")
        assert config.max_backups == 5
        assert config.backup_interval_hours == 12
        assert config.compression is False
        assert config.verify_backups is False

    @patch.dict(os.environ, {
        "BACKUP_SOURCE_DB_PATH": "env.db",
        "BACKUP_DIR": "env_backups",
        "BACKUP_MAX_BACKUPS": "15",
        "BACKUP_INTERVAL_HOURS": "6",
        "BACKUP_COMPRESSION": "false",
        "BACKUP_VERIFY": "false"
    })
    def test_backup_config_from_environment(self):
        """Test BackupConfig initialization from environment variables."""
        config = BackupConfig()
        
        assert config.source_db_path == "env.db"
        assert config.backup_dir == Path("env_backups")
        assert config.max_backups == 15
        assert config.backup_interval_hours == 6
        assert config.compression is False
        assert config.verify_backups is False

    @patch('pathlib.Path.mkdir')
    def test_backup_config_creates_directory(self, mock_mkdir):
        """Test that BackupConfig creates backup directory."""
        BackupConfig(backup_dir="test_dir")
        mock_mkdir.assert_called_once_with(exist_ok=True)

    @patch.dict(os.environ, {}, clear=True)
    def test_backup_config_from_env_classmethod(self):
        """Test BackupConfig.from_env() class method."""
        config = BackupConfig.from_env()
        
        assert config.source_db_path == "viparser.db"
        assert config.backup_dir == Path("backups")

    @patch.dict(os.environ, {"BACKUP_ENABLED": "true"})
    def test_backup_config_is_enabled_true(self):
        """Test is_enabled method returns True."""
        config = BackupConfig()
        assert config.is_enabled() is True

    @patch.dict(os.environ, {"BACKUP_ENABLED": "false"})
    def test_backup_config_is_enabled_false(self):
        """Test is_enabled method returns False."""
        config = BackupConfig()
        assert config.is_enabled() is False

    @patch.dict(os.environ, {}, clear=True)
    def test_backup_config_is_enabled_default(self):
        """Test is_enabled method returns True by default."""
        config = BackupConfig()
        assert config.is_enabled() is True


class TestBackupInfo:
    """Test suite for BackupInfo class."""

    def test_backup_info_initialization(self):
        """Test BackupInfo initialization."""
        created_at = datetime.now()
        filepath = Path("/test/backup.db")
        
        backup_info = BackupInfo(
            filename="backup.db",
            filepath=filepath,
            created_at=created_at,
            size_bytes=1024,
            checksum="abc123",
            compressed=True,
            verified=True
        )
        
        assert backup_info.filename == "backup.db"
        assert backup_info.filepath == filepath
        assert backup_info.created_at == created_at
        assert backup_info.size_bytes == 1024
        assert backup_info.checksum == "abc123"
        assert backup_info.compressed is True
        assert backup_info.verified is True

    def test_backup_info_to_dict(self):
        """Test BackupInfo to_dict method."""
        created_at = datetime(2023, 6, 15, 12, 0, 0)
        filepath = Path("/test/backup.db")
        
        backup_info = BackupInfo(
            filename="backup.db",
            filepath=filepath,
            created_at=created_at,
            size_bytes=2048,
            checksum="def456",
            compressed=False,
            verified=False
        )
        
        result = backup_info.to_dict()
        
        expected = {
            "filename": "backup.db",
            "filepath": str(filepath),  # Use platform-specific path representation
            "created_at": "2023-06-15T12:00:00",
            "size_bytes": 2048,
            "size_human": "2.0 KB",
            "checksum": "def456",
            "compressed": False,
            "verified": False
        }
        
        assert result == expected

    def test_backup_info_format_size_bytes(self):
        """Test format_size method with bytes."""
        backup_info = BackupInfo("test", Path("test"), datetime.now(), 512, "hash")
        assert backup_info.format_size(512) == "512.0 B"

    def test_backup_info_format_size_kb(self):
        """Test format_size method with kilobytes."""
        backup_info = BackupInfo("test", Path("test"), datetime.now(), 512, "hash")
        assert backup_info.format_size(1536) == "1.5 KB"

    def test_backup_info_format_size_mb(self):
        """Test format_size method with megabytes."""
        backup_info = BackupInfo("test", Path("test"), datetime.now(), 512, "hash")
        assert backup_info.format_size(1572864) == "1.5 MB"

    def test_backup_info_format_size_gb(self):
        """Test format_size method with gigabytes."""
        backup_info = BackupInfo("test", Path("test"), datetime.now(), 512, "hash")
        assert backup_info.format_size(1610612736) == "1.5 GB"

    def test_backup_info_format_size_tb(self):
        """Test format_size method with terabytes."""
        backup_info = BackupInfo("test", Path("test"), datetime.now(), 512, "hash")
        assert backup_info.format_size(1649267441664) == "1.5 TB"


class TestDatabaseBackupService:
    """Test suite for DatabaseBackupService class."""

    def setup_method(self):
        """Setup for each test method."""
        self.mock_config = Mock(spec=BackupConfig)
        self.mock_config.backup_dir = Path("/test/backups")
        self.mock_config.source_db_path = "test.db"
        self.mock_config.max_backups = 5
        self.mock_config.backup_interval_hours = 1
        self.mock_config.compression = False
        self.mock_config.verify_backups = False

    def test_backup_service_initialization(self):
        """Test DatabaseBackupService initialization."""
        with patch('services.backup_service.logger') as mock_logger:
            service = DatabaseBackupService(self.mock_config)
            
            assert service.config == self.mock_config
            assert service._backup_task is None
            assert service._running is False
            mock_logger.info.assert_called_once()

    def test_backup_service_initialization_default_config(self):
        """Test DatabaseBackupService initialization with default config."""
        with patch('services.backup_service.BackupConfig') as mock_backup_config:
            mock_config_instance = Mock()
            mock_backup_config.return_value = mock_config_instance
            
            service = DatabaseBackupService()
            
            assert service.config == mock_config_instance
            mock_backup_config.assert_called_once()

    @pytest.mark.asyncio
    async def test_start_scheduled_backups(self):
        """Test starting scheduled backups."""
        service = DatabaseBackupService(self.mock_config)
        
        with patch('asyncio.create_task') as mock_create_task:
            with patch('services.backup_service.logger') as mock_logger:
                mock_task = Mock()
                mock_create_task.return_value = mock_task
                
                await service.start_scheduled_backups()
                
                assert service._running is True
                assert service._backup_task == mock_task
                mock_create_task.assert_called_once()
                mock_logger.info.assert_called_once()

    @pytest.mark.asyncio
    async def test_start_scheduled_backups_already_running(self):
        """Test starting scheduled backups when already running."""
        service = DatabaseBackupService(self.mock_config)
        
        # Mock existing task
        mock_task = Mock()
        mock_task.done.return_value = False
        service._backup_task = mock_task
        
        with patch('services.backup_service.logger') as mock_logger:
            await service.start_scheduled_backups()
            
            mock_logger.warning.assert_called_once()
            assert "already running" in str(mock_logger.warning.call_args)

    @pytest.mark.asyncio
    async def test_stop_scheduled_backups(self):
        """Test stopping scheduled backups."""
        service = DatabaseBackupService(self.mock_config)
        
        # Create a proper future
        mock_future = asyncio.Future()
        mock_future.set_result(None)
        mock_future.cancel = Mock()
        service._backup_task = mock_future
        service._running = True
        
        with patch('services.backup_service.logger') as mock_logger:
            await service.stop_scheduled_backups()
            
            assert service._running is False
            mock_future.cancel.assert_called_once()
            mock_logger.info.assert_called_once()

    @pytest.mark.asyncio
    async def test_stop_scheduled_backups_cancelled_error(self):
        """Test stopping scheduled backups with cancelled error."""
        service = DatabaseBackupService(self.mock_config)
        
        # Create a proper future that will raise CancelledError
        mock_future = asyncio.Future()
        mock_future.set_exception(asyncio.CancelledError())
        mock_future.cancel = Mock()
        service._backup_task = mock_future
        service._running = True
        
        with patch('services.backup_service.logger') as mock_logger:
            await service.stop_scheduled_backups()
            
            assert service._running is False
            mock_logger.info.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_backup_success(self):
        """Test successful backup creation."""
        service = DatabaseBackupService(self.mock_config)
        
        mock_backup_info = Mock(spec=BackupInfo)
        mock_backup_info.size_bytes = 1024
        
        with patch('os.path.exists', return_value=True):
            with patch.object(service, '_create_sqlite_backup', return_value=mock_backup_info) as mock_create:
                with patch.object(service, '_cleanup_old_backups') as mock_cleanup:
                    with patch('services.backup_service.logger') as mock_logger:
                        result = await service.create_backup()
                        
                        assert result == mock_backup_info
                        mock_create.assert_called_once()
                        mock_cleanup.assert_called_once()
                        mock_logger.info.assert_called()

    @pytest.mark.asyncio
    async def test_create_backup_source_not_found(self):
        """Test backup creation when source database not found."""
        service = DatabaseBackupService(self.mock_config)
        
        with patch('os.path.exists', return_value=False):
            with pytest.raises(FileNotFoundError) as exc_info:
                await service.create_backup()
            
            assert "Source database not found" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_list_backups_success(self):
        """Test listing backups successfully."""
        service = DatabaseBackupService(self.mock_config)
        
        # Mock backup files
        mock_file1 = Mock()
        mock_file1.name = "backup1.db"
        mock_file1.stat.return_value.st_ctime = 1234567890
        mock_file1.stat.return_value.st_size = 1024
        mock_file1.suffix = ".db"
        
        mock_file2 = Mock()
        mock_file2.name = "backup2.db.gz"
        mock_file2.stat.return_value.st_ctime = 1234567900
        mock_file2.stat.return_value.st_size = 512
        mock_file2.suffix = ".gz"
        
        # Mock the backup directory
        mock_backup_dir = Mock()
        mock_backup_dir.exists.return_value = True
        mock_backup_dir.glob.return_value = [mock_file1, mock_file2]
        service.config.backup_dir = mock_backup_dir
        
        with patch.object(service, '_calculate_checksum', return_value="hash123"):
            result = await service.list_backups()
            
            assert len(result) == 2
            # Should be sorted by creation time (newest first)
            assert result[0].filename == "backup2.db.gz"
            assert result[1].filename == "backup1.db"

    @pytest.mark.asyncio
    async def test_list_backups_no_directory(self):
        """Test listing backups when directory doesn't exist."""
        service = DatabaseBackupService(self.mock_config)
        
        # Mock the backup directory
        mock_backup_dir = Mock()
        mock_backup_dir.exists.return_value = False
        service.config.backup_dir = mock_backup_dir
        
        result = await service.list_backups()
        
        assert result == []

    @pytest.mark.asyncio
    async def test_restore_backup_success(self):
        """Test restoring backup successfully."""
        service = DatabaseBackupService(self.mock_config)
        backup_filename = "test_backup.db"
        
        # Mock backup directory and path
        mock_backup_path = Mock()
        mock_backup_path.exists.return_value = True
        mock_backup_dir = Mock()
        mock_backup_dir.__truediv__ = Mock(return_value=mock_backup_path)
        service.config.backup_dir = mock_backup_dir
        
        async def mock_executor():
            return None
        
        with patch('asyncio.get_event_loop') as mock_loop:
            with patch('services.backup_service.logger') as mock_logger:
                mock_loop.return_value.run_in_executor.return_value = mock_executor()
                
                result = await service.restore_backup(backup_filename)
                
                assert result is True
                mock_logger.info.assert_called()

    @pytest.mark.asyncio
    async def test_restore_backup_not_found(self):
        """Test restoring backup when file not found."""
        service = DatabaseBackupService(self.mock_config)
        
        # Mock backup directory and path
        mock_backup_path = Mock()
        mock_backup_path.exists.return_value = False
        mock_backup_dir = Mock()
        mock_backup_dir.__truediv__ = Mock(return_value=mock_backup_path)
        service.config.backup_dir = mock_backup_dir
        
        with patch('services.backup_service.logger') as mock_logger:
            result = await service.restore_backup("nonexistent.db")
            
            assert result is False
            mock_logger.error.assert_called()

    @pytest.mark.asyncio
    async def test_delete_backup_success(self):
        """Test successful backup deletion."""
        service = DatabaseBackupService(self.mock_config)
        
        # Mock backup directory and path
        mock_backup_path = Mock()
        mock_backup_path.exists.return_value = True
        mock_backup_dir = Mock()
        mock_backup_dir.__truediv__ = Mock(return_value=mock_backup_path)
        service.config.backup_dir = mock_backup_dir
        
        with patch('os.remove') as mock_remove:
            with patch('services.backup_service.logger') as mock_logger:
                result = await service.delete_backup("test.db")
                
                assert result is True
                mock_remove.assert_called_once_with(mock_backup_path)
                mock_logger.info.assert_called()

    @pytest.mark.asyncio
    async def test_delete_backup_not_found(self):
        """Test deleting backup when file not found."""
        service = DatabaseBackupService(self.mock_config)
        
        # Mock backup directory and path
        mock_backup_path = Mock()
        mock_backup_path.exists.return_value = False
        mock_backup_dir = Mock()
        mock_backup_dir.__truediv__ = Mock(return_value=mock_backup_path)
        service.config.backup_dir = mock_backup_dir
        
        with patch('services.backup_service.logger') as mock_logger:
            result = await service.delete_backup("nonexistent.db")
            
            assert result is False
            mock_logger.error.assert_called()

    @pytest.mark.asyncio
    async def test_get_backup_stats_success(self):
        """Test successful backup statistics retrieval."""
        service = DatabaseBackupService(self.mock_config)
        service._running = True
        
        # Mock backups
        backup1 = Mock()
        backup1.size_bytes = 1024
        backup1.filename = "auto_backup1.db"
        backup1.created_at = datetime(2023, 6, 15, 12, 0, 0)
        backup1._format_size.return_value = "1.5 KB"
        
        backup2 = Mock()
        backup2.size_bytes = 512
        backup2.filename = "manual_backup2.db"
        backup2.created_at = datetime(2023, 6, 14, 12, 0, 0)
        backup2._format_size.return_value = "1.5 KB"
        
        backups = [backup1, backup2]
        
        with patch.object(service, 'list_backups', return_value=backups):
            result = await service.get_backup_stats()
            
            expected = {
                "total_backups": 2,
                "total_size_bytes": 1536,
                "total_size_human": "1.5 KB",
                "oldest_backup": "2023-06-14T12:00:00",
                "newest_backup": "2023-06-15T12:00:00",
                "auto_backups": 1,
                "manual_backups": 1,
                "scheduled_backups_running": True
            }
            
            assert result == expected

    @pytest.mark.asyncio
    async def test_get_backup_stats_no_backups(self):
        """Test backup statistics when no backups exist."""
        service = DatabaseBackupService(self.mock_config)
        
        with patch.object(service, 'list_backups', return_value=[]):
            result = await service.get_backup_stats()
            
            expected = {
                "total_backups": 0,
                "total_size_bytes": 0,
                "total_size_human": "0 B",
                "oldest_backup": None,
                "newest_backup": None,
                "auto_backups": 0,
                "manual_backups": 0
            }
            
            # Check subset since _running state may vary
            for key, value in expected.items():
                assert result[key] == value