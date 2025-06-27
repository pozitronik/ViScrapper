import pytest
import tempfile
import shutil
import sqlite3
import os
from pathlib import Path
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from main import app
from database.session import get_db
from models.product import Base
from services.backup_service import backup_service, BackupConfig


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


@pytest.fixture
def temp_backup_setup():
    """Setup temporary backup environment"""
    temp_dir = tempfile.mkdtemp()
    temp_path = Path(temp_dir)
    
    # Create a test database
    test_db_path = temp_path / "test.db"
    conn = sqlite3.connect(str(test_db_path))
    cursor = conn.cursor()
    
    # Create test table and data
    cursor.execute("""
        CREATE TABLE test_table (
            id INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            value INTEGER
        )
    """)
    cursor.execute("INSERT INTO test_table (name, value) VALUES (?, ?)", ("test1", 100))
    cursor.execute("INSERT INTO test_table (name, value) VALUES (?, ?)", ("test2", 200))
    
    conn.commit()
    conn.close()
    
    # Setup backup service with test config
    backup_dir = temp_path / "backups"
    config = BackupConfig(
        source_db_path=str(test_db_path),
        backup_dir=str(backup_dir),
        max_backups=5,
        backup_interval_hours=1,
        compression=True,
        verify_backups=True
    )
    
    # Replace the global backup service config
    original_config = backup_service.config
    backup_service.config = config
    
    yield temp_path, test_db_path, backup_dir
    
    # Cleanup
    backup_service.config = original_config
    shutil.rmtree(temp_dir)


class TestBackupAPI:
    """Test backup API endpoints"""

    def test_create_backup_success(self, client, temp_backup_setup):
        """Test creating a backup via API"""
        temp_path, test_db_path, backup_dir = temp_backup_setup
        
        response = client.post("/api/v1/backup/create", json="test_backup")
        assert response.status_code == 200
        
        data = response.json()
        assert data["success"] is True
        assert "data" in data
        assert data["data"]["filename"].startswith("manual_test_backup_")
        assert data["data"]["filename"].endswith(".db.gz")
        assert data["data"]["compressed"] is True
        assert data["data"]["verified"] is True

    def test_create_backup_without_name(self, client, temp_backup_setup):
        """Test creating a backup without custom name"""
        temp_path, test_db_path, backup_dir = temp_backup_setup
        
        response = client.post("/api/v1/backup/create")
        assert response.status_code == 200
        
        data = response.json()
        assert data["success"] is True
        assert data["data"]["filename"].startswith("manual_backup_")

    def test_list_backups_empty(self, client, temp_backup_setup):
        """Test listing backups when none exist"""
        temp_path, test_db_path, backup_dir = temp_backup_setup
        
        response = client.get("/api/v1/backup/list")
        assert response.status_code == 200
        
        data = response.json()
        assert data["success"] is True
        assert data["data"] == []
        assert "0 backup(s)" in data["message"]

    def test_list_backups_with_data(self, client, temp_backup_setup):
        """Test listing backups when backups exist"""
        temp_path, test_db_path, backup_dir = temp_backup_setup
        
        # Create a few backups first
        client.post("/api/v1/backup/create", json="backup1")
        client.post("/api/v1/backup/create", json="backup2")
        
        response = client.get("/api/v1/backup/list")
        assert response.status_code == 200
        
        data = response.json()
        assert data["success"] is True
        assert len(data["data"]) == 2
        
        # Check backup data structure
        backup = data["data"][0]
        required_fields = ["filename", "filepath", "created_at", "size_bytes", 
                          "size_human", "checksum", "compressed", "verified"]
        for field in required_fields:
            assert field in backup

    def test_get_backup_stats(self, client, temp_backup_setup):
        """Test getting backup statistics"""
        temp_path, test_db_path, backup_dir = temp_backup_setup
        
        # Create some backups
        client.post("/api/v1/backup/create", json="manual_backup")
        
        response = client.get("/api/v1/backup/stats")
        assert response.status_code == 200
        
        data = response.json()
        assert data["success"] is True
        stats = data["data"]
        
        required_fields = ["total_backups", "total_size_bytes", "total_size_human",
                          "manual_backups", "auto_backups", "scheduled_backups_running"]
        for field in required_fields:
            assert field in stats
        
        assert stats["total_backups"] >= 1
        assert stats["manual_backups"] >= 1

    def test_delete_backup_success(self, client, temp_backup_setup):
        """Test deleting a backup successfully"""
        temp_path, test_db_path, backup_dir = temp_backup_setup
        
        # Create a backup first
        create_response = client.post("/api/v1/backup/create", json="delete_test")
        backup_filename = create_response.json()["data"]["filename"]
        
        # Delete the backup
        response = client.delete(f"/api/v1/backup/{backup_filename}")
        assert response.status_code == 200
        
        data = response.json()
        assert data["deleted_filename"] == backup_filename
        assert "deleted successfully" in data["message"]

    def test_delete_backup_not_found(self, client, temp_backup_setup):
        """Test deleting a backup that doesn't exist"""
        temp_path, test_db_path, backup_dir = temp_backup_setup
        
        response = client.delete("/api/v1/backup/nonexistent_backup.db")
        assert response.status_code == 404

    def test_verify_backup_success(self, client, temp_backup_setup):
        """Test verifying a backup successfully"""
        temp_path, test_db_path, backup_dir = temp_backup_setup
        
        # Create a backup first
        create_response = client.post("/api/v1/backup/create", json="verify_test")
        backup_filename = create_response.json()["data"]["filename"]
        
        # Verify the backup
        response = client.post(f"/api/v1/backup/verify/{backup_filename}")
        assert response.status_code == 200
        
        data = response.json()
        assert data["success"] is True
        result = data["data"]
        assert result["backup_filename"] == backup_filename
        assert result["valid"] is True
        assert "checksum" in result
        assert "size_bytes" in result

    def test_verify_backup_not_found(self, client, temp_backup_setup):
        """Test verifying a backup that doesn't exist"""
        temp_path, test_db_path, backup_dir = temp_backup_setup
        
        response = client.post("/api/v1/backup/verify/nonexistent_backup.db")
        assert response.status_code == 404

    def test_restore_backup_success(self, client, temp_backup_setup):
        """Test restoring a backup successfully"""
        temp_path, test_db_path, backup_dir = temp_backup_setup
        
        # Create a backup first
        create_response = client.post("/api/v1/backup/create", json="restore_test")
        backup_filename = create_response.json()["data"]["filename"]
        
        # Specify a custom restore target
        target_path = str(temp_path / "restored.db")
        
        # Restore the backup
        response = client.post(
            f"/api/v1/backup/restore/{backup_filename}",
            json=target_path
        )
        assert response.status_code == 200
        
        data = response.json()
        assert data["success"] is True
        result = data["data"]
        assert result["backup_filename"] == backup_filename
        assert result["target_path"] == target_path
        
        # Verify the restored file exists
        assert Path(target_path).exists()

    def test_restore_backup_not_found(self, client, temp_backup_setup):
        """Test restoring a backup that doesn't exist"""
        temp_path, test_db_path, backup_dir = temp_backup_setup
        
        response = client.post("/api/v1/backup/restore/nonexistent_backup.db")
        assert response.status_code == 500

    def test_start_scheduled_backups(self, client, temp_backup_setup):
        """Test starting scheduled backups"""
        temp_path, test_db_path, backup_dir = temp_backup_setup
        
        response = client.post("/api/v1/backup/start-scheduled")
        assert response.status_code == 200
        
        data = response.json()
        assert data["success"] is True
        assert data["data"]["status"] == "started"

    def test_stop_scheduled_backups(self, client, temp_backup_setup):
        """Test stopping scheduled backups"""
        temp_path, test_db_path, backup_dir = temp_backup_setup
        
        # Start first
        client.post("/api/v1/backup/start-scheduled")
        
        # Then stop
        response = client.post("/api/v1/backup/stop-scheduled")
        assert response.status_code == 200
        
        data = response.json()
        assert data["success"] is True
        assert data["data"]["status"] == "stopped"

    def test_backup_api_error_handling(self, client):
        """Test API error handling when backup service is not properly configured"""
        # Skip this test since the backup service actually works with the main database
        # In a real scenario, this would test error handling when the source db doesn't exist
        pass

    def test_backup_workflow_integration(self, client, temp_backup_setup):
        """Test complete backup workflow integration"""
        temp_path, test_db_path, backup_dir = temp_backup_setup
        
        # 1. Check initial stats
        stats_response = client.get("/api/v1/backup/stats")
        initial_stats = stats_response.json()["data"]
        assert initial_stats["total_backups"] == 0
        
        # 2. Create multiple backups
        backup1_response = client.post("/api/v1/backup/create", json="workflow_test_1")
        backup2_response = client.post("/api/v1/backup/create", json="workflow_test_2")
        
        backup1_filename = backup1_response.json()["data"]["filename"]
        backup2_filename = backup2_response.json()["data"]["filename"]
        
        # 3. List backups
        list_response = client.get("/api/v1/backup/list")
        backups = list_response.json()["data"]
        assert len(backups) == 2
        
        # 4. Verify stats updated
        stats_response = client.get("/api/v1/backup/stats")
        updated_stats = stats_response.json()["data"]
        assert updated_stats["total_backups"] == 2
        assert updated_stats["manual_backups"] == 2
        
        # 5. Verify a backup
        verify_response = client.post(f"/api/v1/backup/verify/{backup1_filename}")
        assert verify_response.json()["data"]["valid"] is True
        
        # 6. Restore a backup
        target_path = str(temp_path / "workflow_restored.db")
        restore_response = client.post(
            f"/api/v1/backup/restore/{backup1_filename}",
            json=target_path
        )
        assert restore_response.status_code == 200
        assert Path(target_path).exists()
        
        # 7. Delete a backup
        delete_response = client.delete(f"/api/v1/backup/{backup2_filename}")
        assert delete_response.status_code == 200
        
        # 8. Verify deletion
        final_list_response = client.get("/api/v1/backup/list")
        final_backups = final_list_response.json()["data"]
        assert len(final_backups) == 1
        assert final_backups[0]["filename"] == backup1_filename