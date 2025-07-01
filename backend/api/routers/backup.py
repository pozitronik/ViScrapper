"""
API endpoints for database backup management
"""
from fastapi import APIRouter, HTTPException, Body
from typing import List, Optional, Dict, Any

from services.backup_service import backup_service, is_backup_service_enabled
from api.models.responses import SuccessResponse, FileDeleteResponse
from utils.logger import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/api/v1/backup", tags=["Backup"])


def check_backup_service_enabled() -> None:
    """Check if backup service is enabled and available"""
    if backup_service is None:
        raise HTTPException(
            status_code=503,
            detail="Backup service is disabled. Set BACKUP_ENABLED=true in environment variables to enable."
        )


@router.post("/create", response_model=SuccessResponse[Dict[str, Any]])
async def create_backup(
        name: Optional[str] = Body(None, description="Optional backup name"),
) -> SuccessResponse[Dict[str, Any]]:
    """
    Create a new database backup manually.
    
    This creates an immediate backup of the current database state.
    The backup will be stored with a timestamp and optional custom name.
    """
    check_backup_service_enabled()

    # TypeGuard ensures backup_service is not None
    if not is_backup_service_enabled(backup_service):
        # This should never happen after check_backup_service_enabled()
        raise RuntimeError("Backup service unexpectedly None")

    try:
        logger.info(f"Creating manual backup with name: {name}")

        backup_info = await backup_service.create_backup(name=name, auto=False)

        logger.info(f"Manual backup created successfully: {backup_info.filename}")

        return SuccessResponse(
            data=backup_info.to_dict(),
            message=f"Backup created successfully: {backup_info.filename}"
        )

    except Exception as e:
        logger.error(f"Failed to create backup: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to create backup: {str(e)}")


@router.get("/list", response_model=SuccessResponse[List[Dict[str, Any]]])
async def list_backups() -> SuccessResponse[List[Dict[str, Any]]]:
    """
    List all available database backups.
    
    Returns information about all backup files including:
    - Filename and creation date
    - File size and checksum
    - Compression and verification status
    """
    check_backup_service_enabled()

    # TypeGuard ensures backup_service is not None
    if not is_backup_service_enabled(backup_service):
        raise RuntimeError("Backup service unexpectedly None")

    try:
        logger.info("Listing all backups")

        backups = await backup_service.list_backups()
        backup_data = [backup.to_dict() for backup in backups]

        logger.info(f"Found {len(backups)} backups")

        return SuccessResponse(
            data=backup_data,
            message=f"Found {len(backups)} backup(s)"
        )

    except Exception as e:
        logger.error(f"Failed to list backups: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to list backups: {str(e)}")


@router.get("/stats", response_model=SuccessResponse[Dict[str, Any]])
async def get_backup_stats() -> SuccessResponse[Dict[str, Any]]:
    """
    Get backup statistics and information.
    
    Returns summary statistics about the backup system including:
    - Total number of backups and storage used
    - Oldest and newest backup dates
    - Count of automatic vs manual backups
    - Scheduled backup status
    """
    check_backup_service_enabled()

    # TypeGuard ensures backup_service is not None
    if not is_backup_service_enabled(backup_service):
        raise RuntimeError("Backup service unexpectedly None")

    try:
        logger.info("Getting backup statistics")

        stats = await backup_service.get_backup_stats()

        return SuccessResponse(
            data=stats,
            message="Backup statistics retrieved successfully"
        )

    except Exception as e:
        logger.error(f"Failed to get backup stats: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get backup stats: {str(e)}")


@router.post("/restore/{backup_filename}", response_model=SuccessResponse[Dict[str, Any]])
async def restore_backup(
        backup_filename: str,
        target_path: Optional[str] = Body(None, description="Optional target path for restore")
) -> SuccessResponse[Dict[str, Any]]:
    """
    Restore a database from a backup file.
    
    **WARNING**: This will overwrite the current database!
    Make sure to create a backup of the current state before restoring.
    
    Args:
        backup_filename: Name of the backup file to restore
        target_path: Optional target path (defaults to main database)
    """
    check_backup_service_enabled()

    # TypeGuard ensures backup_service is not None
    if not is_backup_service_enabled(backup_service):
        raise RuntimeError("Backup service unexpectedly None")

    try:
        logger.warning(f"Restoring backup: {backup_filename} to {target_path or 'main database'}")

        success = await backup_service.restore_backup(backup_filename, target_path)

        if not success:
            raise HTTPException(status_code=500, detail="Backup restore failed")

        logger.info(f"Backup restored successfully: {backup_filename}")

        return SuccessResponse(
            data={"backup_filename": backup_filename, "target_path": target_path},
            message=f"Backup restored successfully: {backup_filename}"
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to restore backup {backup_filename}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to restore backup: {str(e)}")


@router.delete("/{backup_filename}", response_model=FileDeleteResponse)
async def delete_backup(backup_filename: str) -> FileDeleteResponse:
    """
    Delete a specific backup file.
    
    This permanently removes the backup file from storage.
    This action cannot be undone.
    
    Args:
        backup_filename: Name of the backup file to delete
    """
    check_backup_service_enabled()

    # TypeGuard ensures backup_service is not None
    if not is_backup_service_enabled(backup_service):
        raise RuntimeError("Backup service unexpectedly None")

    try:
        logger.info(f"Deleting backup: {backup_filename}")

        success = await backup_service.delete_backup(backup_filename)

        if not success:
            raise HTTPException(status_code=404, detail=f"Backup not found: {backup_filename}")

        logger.info(f"Backup deleted successfully: {backup_filename}")

        return FileDeleteResponse(
            deleted_filename=backup_filename,
            message=f"Backup deleted successfully: {backup_filename}"
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete backup {backup_filename}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to delete backup: {str(e)}")


@router.post("/start-scheduled", response_model=SuccessResponse[Dict[str, Any]])
async def start_scheduled_backups() -> SuccessResponse[Dict[str, Any]]:
    """
    Start automatic scheduled backups.
    
    This enables the background task that creates automatic backups
    at regular intervals according to the configured schedule.
    """
    check_backup_service_enabled()

    # TypeGuard ensures backup_service is not None
    if not is_backup_service_enabled(backup_service):
        raise RuntimeError("Backup service unexpectedly None")

    try:
        logger.info("Starting scheduled backups")

        await backup_service.start_scheduled_backups()

        return SuccessResponse(
            data={"status": "started"},
            message="Scheduled backups started successfully"
        )

    except Exception as e:
        logger.error(f"Failed to start scheduled backups: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to start scheduled backups: {str(e)}")


@router.post("/stop-scheduled", response_model=SuccessResponse[Dict[str, Any]])
async def stop_scheduled_backups() -> SuccessResponse[Dict[str, Any]]:
    """
    Stop automatic scheduled backups.
    
    This disables the background task that creates automatic backups.
    Manual backups can still be created.
    """
    check_backup_service_enabled()

    # TypeGuard ensures backup_service is not None
    if not is_backup_service_enabled(backup_service):
        raise RuntimeError("Backup service unexpectedly None")

    try:
        logger.info("Stopping scheduled backups")

        await backup_service.stop_scheduled_backups()

        return SuccessResponse(
            data={"status": "stopped"},
            message="Scheduled backups stopped successfully"
        )

    except Exception as e:
        logger.error(f"Failed to stop scheduled backups: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to stop scheduled backups: {str(e)}")


@router.post("/verify/{backup_filename}", response_model=SuccessResponse[Dict[str, Any]])
async def verify_backup(backup_filename: str) -> SuccessResponse[Dict[str, Any]]:
    """
    Verify the integrity of a specific backup file.
    
    This checks if the backup file is valid and can be used for restoration.
    Verification includes checking file integrity and SQLite database validity.
    
    Args:
        backup_filename: Name of the backup file to verify
    """
    check_backup_service_enabled()

    # TypeGuard ensures backup_service is not None
    if not is_backup_service_enabled(backup_service):
        raise RuntimeError("Backup service unexpectedly None")

    try:
        logger.info(f"Verifying backup: {backup_filename}")

        # Find the backup in the list
        backups = await backup_service.list_backups()
        backup_info = None

        for backup in backups:
            if backup.filename == backup_filename:
                backup_info = backup
                break

        if not backup_info:
            raise HTTPException(status_code=404, detail=f"Backup not found: {backup_filename}")

        # Verify the backup
        is_valid = await backup_service.verify_backup(backup_info)

        result = {
            "backup_filename": backup_filename,
            "valid": is_valid,
            "checksum": backup_info.checksum,
            "size_bytes": backup_info.size_bytes
        }

        message = f"Backup verification {'passed' if is_valid else 'failed'}: {backup_filename}"
        logger.info(message)

        return SuccessResponse(
            data=result,
            message=message
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to verify backup {backup_filename}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to verify backup: {str(e)}")
