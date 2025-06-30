"""
Database backup service for VIParser
"""
import os
import shutil
import sqlite3
import asyncio
from datetime import datetime
from typing import List, Dict, Optional, Any
from pathlib import Path
import hashlib
import gzip

from utils.logger import get_logger

logger = get_logger(__name__)


class BackupConfig:
    """Configuration for backup service"""
    
    def __init__(
        self,
        source_db_path: Optional[str] = None,
        backup_dir: Optional[str] = None,
        max_backups: Optional[int] = None,
        backup_interval_hours: Optional[int] = None,
        compression: Optional[bool] = None,
        verify_backups: Optional[bool] = None
    ) -> None:
        # Load from environment variables with fallback to defaults
        self.source_db_path: str = source_db_path or os.getenv("BACKUP_SOURCE_DB_PATH") or "viparser.db"
        self.backup_dir: Path = Path(backup_dir or os.getenv("BACKUP_DIR") or "backups")
        self.max_backups: int = max_backups if max_backups is not None else int(os.getenv("BACKUP_MAX_BACKUPS", "10"))
        self.backup_interval_hours: int = backup_interval_hours if backup_interval_hours is not None else int(os.getenv("BACKUP_INTERVAL_HOURS", "24"))
        self.compression: bool = compression if compression is not None else os.getenv("BACKUP_COMPRESSION", "true").lower() == "true"
        self.verify_backups: bool = verify_backups if verify_backups is not None else os.getenv("BACKUP_VERIFY", "true").lower() == "true"
        
        # Ensure backup directory exists
        self.backup_dir.mkdir(exist_ok=True)
    
    @classmethod
    def from_env(cls) -> "BackupConfig":
        """Create configuration from environment variables only"""
        return cls()
    
    def is_enabled(self) -> bool:
        """Check if backup system is enabled via environment variable"""
        return os.getenv("BACKUP_ENABLED", "true").lower() == "true"


class BackupInfo:
    """Information about a backup"""
    
    def __init__(
        self,
        filename: str,
        filepath: Path,
        created_at: datetime,
        size_bytes: int,
        checksum: str,
        compressed: bool = False,
        verified: bool = False
    ):
        self.filename = filename
        self.filepath = filepath
        self.created_at = created_at
        self.size_bytes = size_bytes
        self.checksum = checksum
        self.compressed = compressed
        self.verified = verified
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return {
            "filename": self.filename,
            "filepath": str(self.filepath),
            "created_at": self.created_at.isoformat(),
            "size_bytes": self.size_bytes,
            "size_human": self._format_size(self.size_bytes),
            "checksum": self.checksum,
            "compressed": self.compressed,
            "verified": self.verified
        }
    
    def _format_size(self, size_bytes: int) -> str:
        """Format file size in human readable format"""
        size_float = float(size_bytes)
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size_float < 1024.0:
                return f"{size_float:.1f} {unit}"
            size_float /= 1024.0
        return f"{size_float:.1f} TB"


class DatabaseBackupService:
    """Service for managing database backups"""
    
    def __init__(self, config: Optional[BackupConfig] = None) -> None:
        self.config = config or BackupConfig()
        self._backup_task = None
        self._running = False
        
        logger.info(f"Backup service initialized - backup dir: {self.config.backup_dir}")
    
    async def start_scheduled_backups(self) -> None:
        """Start the scheduled backup task"""
        if self._backup_task and not self._backup_task.done():
            logger.warning("Scheduled backups already running")
            return
        
        self._running = True
        self._backup_task = asyncio.create_task(self._backup_scheduler())
        logger.info(f"Started scheduled backups every {self.config.backup_interval_hours} hours")
    
    async def stop_scheduled_backups(self) -> None:
        """Stop the scheduled backup task"""
        self._running = False
        if self._backup_task:
            self._backup_task.cancel()
            try:
                await self._backup_task
            except asyncio.CancelledError:
                pass
        logger.info("Stopped scheduled backups")
    
    async def _backup_scheduler(self) -> None:
        """Background task for scheduled backups"""
        while self._running:
            try:
                # Wait for the backup interval
                await asyncio.sleep(self.config.backup_interval_hours * 3600)
                
                if not self._running:
                    break
                
                # Perform automatic backup
                logger.info("Starting scheduled backup")
                await self.create_backup(auto=True)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in backup scheduler: {e}")
                # Continue running even if one backup fails
                await asyncio.sleep(300)  # Wait 5 minutes before retry
    
    async def create_backup(self, name: Optional[str] = None, auto: bool = False) -> BackupInfo:
        """Create a new database backup"""
        try:
            # Generate backup filename
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            prefix = "auto" if auto else "manual"
            if name:
                backup_name = f"{prefix}_{name}_{timestamp}.db"
            else:
                backup_name = f"{prefix}_backup_{timestamp}.db"
            
            if self.config.compression:
                backup_name += ".gz"
            
            backup_path = self.config.backup_dir / backup_name
            
            logger.info(f"Creating backup: {backup_path}")
            
            # Check if source database exists
            if not os.path.exists(self.config.source_db_path):
                raise FileNotFoundError(f"Source database not found: {self.config.source_db_path}")
            
            # Create backup using SQLite backup API for consistency
            backup_info = await self._create_sqlite_backup(backup_path)
            
            # Verify backup if enabled
            if self.config.verify_backups:
                is_valid = await self._verify_backup(backup_info)
                backup_info.verified = is_valid
                if not is_valid:
                    logger.error(f"Backup verification failed: {backup_path}")
                    # Don't delete the backup, let user decide
                else:
                    logger.info(f"Backup verified successfully: {backup_path}")
            
            # Clean up old backups
            await self._cleanup_old_backups()
            
            logger.info(f"Backup created successfully: {backup_path} ({backup_info.size_bytes} bytes)")
            return backup_info
            
        except Exception as e:
            logger.error(f"Failed to create backup: {e}")
            raise
    
    async def _create_sqlite_backup(self, backup_path: Path) -> BackupInfo:
        """Create backup using SQLite's backup API"""
        def _backup_db() -> BackupInfo:
            # Connect to source database
            source_conn = sqlite3.connect(self.config.source_db_path)
            
            try:
                if self.config.compression:
                    # Create temporary uncompressed backup first
                    temp_path = backup_path.with_suffix('')
                    
                    # Create backup connection
                    backup_conn = sqlite3.connect(str(temp_path))
                    
                    try:
                        # Perform backup using SQLite backup API
                        source_conn.backup(backup_conn)
                        backup_conn.close()
                        
                        # Compress the backup
                        with open(temp_path, 'rb') as f_in:
                            with gzip.open(backup_path, 'wb') as f_out:
                                shutil.copyfileobj(f_in, f_out)
                        
                        # Remove temporary file
                        os.remove(temp_path)
                        
                    except Exception:
                        backup_conn.close()
                        if temp_path.exists():
                            os.remove(temp_path)
                        raise
                else:
                    # Direct backup without compression
                    backup_conn = sqlite3.connect(str(backup_path))
                    try:
                        source_conn.backup(backup_conn)
                    finally:
                        backup_conn.close()
                
            finally:
                source_conn.close()
        
        # Run backup in thread to avoid blocking
        await asyncio.get_event_loop().run_in_executor(None, _backup_db)
        
        # Get backup file info
        stat = backup_path.stat()
        checksum = await self._calculate_checksum(backup_path)
        
        return BackupInfo(
            filename=backup_path.name,
            filepath=backup_path,
            created_at=datetime.fromtimestamp(stat.st_ctime),
            size_bytes=stat.st_size,
            checksum=checksum,
            compressed=self.config.compression,
            verified=False
        )
    
    async def _verify_backup(self, backup_info: BackupInfo) -> bool:
        """Verify backup integrity"""
        try:
            def _verify() -> bool:
                if backup_info.compressed:
                    # Verify compressed backup by attempting to decompress and check
                    with gzip.open(backup_info.filepath, 'rb') as f:
                        # Try to open as SQLite database
                        temp_path = backup_info.filepath.with_suffix('.verify_temp')
                        try:
                            with open(temp_path, 'wb') as temp_f:
                                shutil.copyfileobj(f, temp_f)
                            
                            # Test SQLite connection
                            conn = sqlite3.connect(str(temp_path))
                            try:
                                cursor = conn.cursor()
                                cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
                                tables = cursor.fetchall()
                                return len(tables) > 0  # Should have at least one table
                            finally:
                                conn.close()
                        finally:
                            if temp_path.exists():
                                os.remove(temp_path)
                else:
                    # Verify uncompressed backup
                    conn = sqlite3.connect(str(backup_info.filepath))
                    try:
                        cursor = conn.cursor()
                        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
                        tables = cursor.fetchall()
                        return len(tables) > 0  # Should have at least one table
                    finally:
                        conn.close()
            
            # Run verification in thread
            return await asyncio.get_event_loop().run_in_executor(None, _verify)
            
        except Exception as e:
            logger.error(f"Backup verification failed: {e}")
            return False
    
    async def _calculate_checksum(self, filepath: Path) -> str:
        """Calculate SHA256 checksum of a file"""
        def _calc() -> str:
            hash_sha256 = hashlib.sha256()
            with open(filepath, "rb") as f:
                for chunk in iter(lambda: f.read(4096), b""):
                    hash_sha256.update(chunk)
            return hash_sha256.hexdigest()
        
        return await asyncio.get_event_loop().run_in_executor(None, _calc)
    
    async def list_backups(self) -> List[BackupInfo]:
        """List all available backups"""
        backups = []
        
        if not self.config.backup_dir.exists():
            return backups
        
        for backup_file in self.config.backup_dir.glob("*.db*"):
            try:
                stat = backup_file.stat()
                checksum = await self._calculate_checksum(backup_file)
                
                backup_info = BackupInfo(
                    filename=backup_file.name,
                    filepath=backup_file,
                    created_at=datetime.fromtimestamp(stat.st_ctime),
                    size_bytes=stat.st_size,
                    checksum=checksum,
                    compressed=backup_file.suffix == '.gz',
                    verified=False  # Don't verify during listing for performance
                )
                
                backups.append(backup_info)
                
            except Exception as e:
                logger.warning(f"Error reading backup file {backup_file}: {e}")
        
        # Sort by creation time (newest first)
        backups.sort(key=lambda x: x.created_at, reverse=True)
        return backups
    
    async def restore_backup(self, backup_filename: str, target_path: Optional[str] = None) -> bool:
        """Restore a backup to the main database"""
        try:
            backup_path = self.config.backup_dir / backup_filename
            if not backup_path.exists():
                raise FileNotFoundError(f"Backup file not found: {backup_filename}")
            
            target = target_path or self.config.source_db_path
            
            logger.info(f"Restoring backup {backup_filename} to {target}")
            
            def _restore() -> None:
                if backup_filename.endswith('.gz'):
                    # Decompress and restore
                    with gzip.open(backup_path, 'rb') as f_in:
                        with open(target, 'wb') as f_out:
                            shutil.copyfileobj(f_in, f_out)
                else:
                    # Direct copy
                    shutil.copy2(backup_path, target)
            
            # Run restore in thread
            await asyncio.get_event_loop().run_in_executor(None, _restore)
            
            logger.info(f"Backup restored successfully: {backup_filename}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to restore backup {backup_filename}: {e}")
            return False
    
    async def delete_backup(self, backup_filename: str) -> bool:
        """Delete a specific backup"""
        try:
            backup_path = self.config.backup_dir / backup_filename
            if not backup_path.exists():
                raise FileNotFoundError(f"Backup file not found: {backup_filename}")
            
            os.remove(backup_path)
            logger.info(f"Backup deleted: {backup_filename}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to delete backup {backup_filename}: {e}")
            return False
    
    async def _cleanup_old_backups(self) -> None:
        """Remove old backups according to retention policy"""
        try:
            backups = await self.list_backups()
            
            if len(backups) <= self.config.max_backups:
                return
            
            # Keep only the newest backups
            backups_to_delete = backups[self.config.max_backups:]
            
            for backup in backups_to_delete:
                try:
                    os.remove(backup.filepath)
                    logger.info(f"Deleted old backup: {backup.filename}")
                except Exception as e:
                    logger.warning(f"Failed to delete old backup {backup.filename}: {e}")
                    
        except Exception as e:
            logger.error(f"Error during backup cleanup: {e}")
    
    async def get_backup_stats(self) -> Dict[str, Any]:
        """Get backup statistics"""
        try:
            backups = await self.list_backups()
            
            if not backups:
                return {
                    "total_backups": 0,
                    "total_size_bytes": 0,
                    "total_size_human": "0 B",
                    "oldest_backup": None,
                    "newest_backup": None,
                    "auto_backups": 0,
                    "manual_backups": 0
                }
            
            total_size = sum(b.size_bytes for b in backups)
            auto_count = len([b for b in backups if b.filename.startswith('auto_')])
            manual_count = len(backups) - auto_count
            
            return {
                "total_backups": len(backups),
                "total_size_bytes": total_size,
                "total_size_human": backups[0]._format_size(total_size),
                "oldest_backup": backups[-1].created_at.isoformat() if backups else None,
                "newest_backup": backups[0].created_at.isoformat() if backups else None,
                "auto_backups": auto_count,
                "manual_backups": manual_count,
                "scheduled_backups_running": self._running
            }
            
        except Exception as e:
            logger.error(f"Error getting backup stats: {e}")
            return {"error": str(e)}


# Global backup service instance with environment configuration
_backup_config = BackupConfig.from_env()
backup_service = DatabaseBackupService(_backup_config) if _backup_config.is_enabled() else None