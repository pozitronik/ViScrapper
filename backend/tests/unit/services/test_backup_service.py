import pytest
import asyncio
import tempfile
import shutil
import sqlite3
import os
from pathlib import Path
from datetime import datetime, timedelta

from services.backup_service import DatabaseBackupService, BackupConfig, BackupInfo


class TestBackupService:
    """Test backup service functionality"""
    
    @pytest.fixture
    def temp_dir(self):
        """Create temporary directory for testing"""
        temp_dir = tempfile.mkdtemp()
        yield Path(temp_dir)
        shutil.rmtree(temp_dir)
    
    @pytest.fixture
    def test_db_path(self, temp_dir):
        """Create a test SQLite database"""
        db_path = temp_dir / "test.db"
        
        # Create a simple test database
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()
        
        # Create test table
        cursor.execute("""
            CREATE TABLE test_products (
                id INTEGER PRIMARY KEY,
                name TEXT NOT NULL,
                price REAL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Insert test data
        cursor.execute("INSERT INTO test_products (name, price) VALUES (?, ?)", ("Test Product 1", 19.99))
        cursor.execute("INSERT INTO test_products (name, price) VALUES (?, ?)", ("Test Product 2", 29.99))
        cursor.execute("INSERT INTO test_products (name, price) VALUES (?, ?)", ("Test Product 3", 39.99))
        
        conn.commit()
        conn.close()
        
        return db_path
    
    @pytest.fixture
    def backup_config(self, test_db_path, temp_dir):
        """Create backup configuration for testing"""
        backup_dir = temp_dir / "backups"
        return BackupConfig(
            source_db_path=str(test_db_path),
            backup_dir=str(backup_dir),
            max_backups=3,
            backup_interval_hours=1,
            compression=True,
            verify_backups=True
        )
    
    @pytest.fixture
    def backup_service(self, backup_config):
        """Create backup service instance"""
        return DatabaseBackupService(backup_config)
    
    @pytest.mark.asyncio
    async def test_create_manual_backup(self, backup_service):
        """Test creating a manual backup"""
        backup_info = await backup_service.create_backup(name="test_manual", auto=False)
        
        assert backup_info.filename.startswith("manual_test_manual_")
        assert backup_info.filename.endswith(".db.gz")
        assert backup_info.filepath.exists()
        assert backup_info.size_bytes > 0
        assert backup_info.checksum is not None
        assert backup_info.compressed is True
        assert backup_info.verified is True
    
    @pytest.mark.asyncio
    async def test_create_auto_backup(self, backup_service):
        """Test creating an automatic backup"""
        backup_info = await backup_service.create_backup(auto=True)
        
        assert backup_info.filename.startswith("auto_backup_")
        assert backup_info.filename.endswith(".db.gz")
        assert backup_info.filepath.exists()
        assert backup_info.size_bytes > 0
        assert backup_info.compressed is True
        assert backup_info.verified is True
    
    @pytest.mark.asyncio
    async def test_backup_without_compression(self, test_db_path, temp_dir):
        """Test creating backup without compression"""
        backup_dir = temp_dir / "backups_uncompressed"
        config = BackupConfig(
            source_db_path=str(test_db_path),
            backup_dir=str(backup_dir),
            compression=False,
            verify_backups=True
        )
        service = DatabaseBackupService(config)
        
        backup_info = await service.create_backup(name="uncompressed")
        
        assert backup_info.filename.endswith(".db")
        assert not backup_info.filename.endswith(".gz")
        assert backup_info.compressed is False
        assert backup_info.verified is True
    
    @pytest.mark.asyncio
    async def test_list_backups(self, backup_service):
        """Test listing backups"""
        # Create multiple backups
        await backup_service.create_backup(name="backup1")
        await backup_service.create_backup(name="backup2")
        await backup_service.create_backup(name="backup3")
        
        backups = await backup_service.list_backups()
        
        assert len(backups) == 3
        # Should be sorted by creation time (newest first)
        assert backups[0].created_at >= backups[1].created_at
        assert backups[1].created_at >= backups[2].created_at
    
    @pytest.mark.asyncio
    async def test_backup_cleanup(self, backup_service):
        """Test automatic cleanup of old backups"""
        # Create more backups than max_backups (3)
        for i in range(5):
            await backup_service.create_backup(name=f"backup_{i}")
        
        backups = await backup_service.list_backups()
        
        # Should only have max_backups (3) remaining
        assert len(backups) <= backup_service.config.max_backups
    
    @pytest.mark.asyncio
    async def test_restore_backup(self, backup_service, temp_dir):
        """Test restoring a backup"""
        # Create a backup
        backup_info = await backup_service.create_backup(name="restore_test")
        
        # Create a different target file
        target_path = temp_dir / "restored.db"
        
        # Restore the backup
        success = await backup_service.restore_backup(backup_info.filename, str(target_path))
        
        assert success is True
        assert target_path.exists()
        
        # Verify restored database has correct data
        conn = sqlite3.connect(str(target_path))
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM test_products")
        count = cursor.fetchone()[0]
        conn.close()
        
        assert count == 3  # Should have 3 test products
    
    @pytest.mark.asyncio
    async def test_delete_backup(self, backup_service):
        """Test deleting a backup"""
        # Create a backup
        backup_info = await backup_service.create_backup(name="delete_test")
        
        # Verify backup exists
        assert backup_info.filepath.exists()
        
        # Delete the backup
        success = await backup_service.delete_backup(backup_info.filename)
        
        assert success is True
        assert not backup_info.filepath.exists()
    
    @pytest.mark.asyncio
    async def test_delete_nonexistent_backup(self, backup_service):
        """Test deleting a backup that doesn't exist"""
        success = await backup_service.delete_backup("nonexistent_backup.db")
        assert success is False
    
    @pytest.mark.asyncio
    async def test_verify_backup(self, backup_service):
        """Test backup verification"""
        # Create a backup
        backup_info = await backup_service.create_backup(name="verify_test")
        
        # Verify the backup
        is_valid = await backup_service._verify_backup(backup_info)
        
        assert is_valid is True
    
    @pytest.mark.asyncio
    async def test_backup_stats(self, backup_service):
        """Test backup statistics"""
        # Create some backups
        await backup_service.create_backup(name="stats1", auto=False)
        await backup_service.create_backup(auto=True)
        await backup_service.create_backup(name="stats2", auto=False)
        
        stats = await backup_service.get_backup_stats()
        
        assert stats["total_backups"] == 3
        assert stats["total_size_bytes"] > 0
        assert stats["manual_backups"] == 2
        assert stats["auto_backups"] == 1
        assert "oldest_backup" in stats
        assert "newest_backup" in stats
    
    @pytest.mark.asyncio
    async def test_backup_with_missing_source(self, temp_dir):
        """Test backup creation when source database doesn't exist"""
        config = BackupConfig(
            source_db_path=str(temp_dir / "nonexistent.db"),
            backup_dir=str(temp_dir / "backups")
        )
        service = DatabaseBackupService(config)
        
        with pytest.raises(FileNotFoundError):
            await service.create_backup(name="should_fail")
    
    @pytest.mark.asyncio
    async def test_scheduled_backups_start_stop(self, backup_service):
        """Test starting and stopping scheduled backups"""
        # Start scheduled backups
        await backup_service.start_scheduled_backups()
        assert backup_service._running is True
        assert backup_service._backup_task is not None
        
        # Stop scheduled backups
        await backup_service.stop_scheduled_backups()
        assert backup_service._running is False
    
    @pytest.mark.asyncio
    async def test_backup_info_serialization(self, backup_service):
        """Test BackupInfo serialization to dict"""
        backup_info = await backup_service.create_backup(name="serialize_test")
        
        data = backup_info.to_dict()
        
        assert "filename" in data
        assert "filepath" in data
        assert "created_at" in data
        assert "size_bytes" in data
        assert "size_human" in data
        assert "checksum" in data
        assert "compressed" in data
        assert "verified" in data
        
        # Check that datetime is properly serialized
        datetime.fromisoformat(data["created_at"])  # Should not raise exception
    
    @pytest.mark.asyncio
    async def test_backup_checksum_consistency(self, backup_service):
        """Test that backup checksums are consistent"""
        backup_info = await backup_service.create_backup(name="checksum_test")
        
        # Calculate checksum again
        new_checksum = await backup_service._calculate_checksum(backup_info.filepath)
        
        assert backup_info.checksum == new_checksum
    
    @pytest.mark.asyncio
    async def test_backup_config_validation(self, test_db_path, temp_dir):
        """Test backup configuration validation"""
        # Test with valid config
        config = BackupConfig(
            source_db_path=str(test_db_path),
            backup_dir=str(temp_dir / "backups"),
            max_backups=5,
            backup_interval_hours=2
        )
        
        assert config.source_db_path == str(test_db_path)
        assert config.max_backups == 5
        assert config.backup_interval_hours == 2
        assert config.backup_dir.exists()  # Should be created automatically
    
    @pytest.mark.asyncio
    async def test_compressed_backup_restore(self, backup_service, temp_dir):
        """Test restoring a compressed backup"""
        # Create compressed backup
        backup_info = await backup_service.create_backup(name="compressed_test")
        assert backup_info.compressed is True
        
        # Restore to a new location
        target_path = temp_dir / "restored_compressed.db"
        success = await backup_service.restore_backup(backup_info.filename, str(target_path))
        
        assert success is True
        assert target_path.exists()
        
        # Verify restored data
        conn = sqlite3.connect(str(target_path))
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM test_products ORDER BY id")
        products = cursor.fetchall()
        conn.close()
        
        expected_products = [("Test Product 1",), ("Test Product 2",), ("Test Product 3",)]
        assert products == expected_products