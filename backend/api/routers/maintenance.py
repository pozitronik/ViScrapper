"""
Maintenance API endpoints for system cleanup and optimization.
"""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from typing import Dict, Any

from database.session import get_db
from services.image_cleanup_service import image_cleanup_service, CleanupResult
from api.models.responses import SuccessResponse
from utils.logger import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/api/v1/maintenance", tags=["Maintenance"])


@router.post("/cleanup-orphaned-images", response_model=SuccessResponse[CleanupResult])
async def cleanup_orphaned_images(
        dry_run: bool = Query(True, description="Simulate cleanup without actually deleting files"),
        db: Session = Depends(get_db)
) -> SuccessResponse[CleanupResult]:
    """
    Clean up orphaned image files that exist in filesystem but are not referenced in database.
    
    This endpoint helps maintain storage efficiency by removing image files that are no longer
    needed. Use dry_run=true to see what would be deleted before actually deleting.
    """
    logger.info(f"Starting orphaned image cleanup (dry_run={dry_run})")

    # Perform cleanup
    results = image_cleanup_service.cleanup_orphaned_images(dry_run=dry_run)

    # Determine appropriate message
    action = "Would delete" if dry_run else "Deleted"
    message = f"{action} {results['deleted_count']} orphaned images, freed {results['total_size_freed']} bytes"

    if results['failed_count'] > 0:
        message += f", {results['failed_count']} files failed to delete"

    logger.info(f"Orphaned image cleanup completed: {message}")

    return SuccessResponse(
        data=results,
        message=message
    )


@router.get("/image-statistics", response_model=SuccessResponse[Dict[str, Any]])
async def get_image_statistics(db: Session = Depends(get_db)) -> SuccessResponse[Dict[str, Any]]:
    """
    Get statistics about image files and storage usage.
    """
    logger.info("Getting image statistics")

    try:
        # Get database image count
        db_images = image_cleanup_service.get_database_image_files(db)

        # Get filesystem image count
        fs_images = image_cleanup_service.get_filesystem_image_files()

        # Find orphaned images
        orphaned_images = image_cleanup_service.find_orphaned_images(db)

        # Calculate total filesystem size
        total_size = 0
        orphaned_size = 0

        for filename in fs_images:
            file_path = image_cleanup_service.image_dir / filename
            if file_path.exists():
                file_size = file_path.stat().st_size
                total_size += file_size

                if filename in orphaned_images:
                    orphaned_size += file_size

        statistics = {
            'database_images': len(db_images),
            'filesystem_images': len(fs_images),
            'orphaned_images': len(orphaned_images),
            'total_filesystem_size_bytes': total_size,
            'orphaned_size_bytes': orphaned_size,
            'total_filesystem_size_mb': round(total_size / (1024 * 1024), 2),
            'orphaned_size_mb': round(orphaned_size / (1024 * 1024), 2),
            'storage_efficiency_percent': round(
                ((total_size - orphaned_size) / total_size * 100) if total_size > 0 else 100, 2
            ),
            'image_directory': str(image_cleanup_service.image_dir)
        }

        logger.info(f"Image statistics: {statistics}")

        return SuccessResponse(
            data=statistics,
            message="Image statistics retrieved successfully"
        )

    except Exception as e:
        logger.error(f"Error getting image statistics: {e}")
        raise
