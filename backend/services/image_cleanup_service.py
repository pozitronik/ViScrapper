"""
Image cleanup service for removing orphaned images.
"""

import os
import asyncio
from pathlib import Path
from typing import List, Set
from sqlalchemy.orm import Session
from models.product import Image
from database.session import get_db
from utils.logger import get_logger

logger = get_logger(__name__)
IMAGE_DIR = os.getenv("IMAGE_DIR", "./images")


class ImageCleanupService:
    """Service for cleaning up orphaned image files."""
    
    def __init__(self, image_dir: str = IMAGE_DIR):
        self.image_dir = Path(image_dir)
        
    def get_database_image_files(self, db: Session) -> Set[str]:
        """
        Get all image filenames referenced in the database.
        
        Args:
            db: Database session
            
        Returns:
            Set of image filenames referenced in database
        """
        try:
            # Get all image URLs from database (both active and soft-deleted)
            images = db.query(Image).all()
            
            # Extract just the filename from URLs that look like local file IDs
            db_filenames = set()
            for image in images:
                if image.url and not image.url.startswith(('http://', 'https://')):
                    # This is a local file ID, add it to the set
                    db_filenames.add(image.url)
            
            logger.info(f"Found {len(db_filenames)} image files referenced in database")
            return db_filenames
            
        except Exception as e:
            logger.error(f"Error getting database image files: {e}")
            return set()
    
    def get_filesystem_image_files(self) -> Set[str]:
        """
        Get all image files present in the filesystem.
        
        Returns:
            Set of image filenames in filesystem
        """
        try:
            if not self.image_dir.exists():
                logger.warning(f"Image directory {self.image_dir} does not exist")
                return set()
            
            # Get all files in image directory
            image_extensions = {'.jpg', '.jpeg', '.png', '.gif', '.webp', '.bmp'}
            filesystem_files = set()
            
            for file_path in self.image_dir.iterdir():
                if file_path.is_file() and file_path.suffix.lower() in image_extensions:
                    filesystem_files.add(file_path.name)
            
            logger.info(f"Found {len(filesystem_files)} image files in filesystem")
            return filesystem_files
            
        except Exception as e:
            logger.error(f"Error scanning filesystem for images: {e}")
            return set()
    
    def find_orphaned_images(self, db: Session) -> List[str]:
        """
        Find image files that exist in filesystem but are not referenced in database.
        
        Args:
            db: Database session
            
        Returns:
            List of orphaned image filenames
        """
        db_files = self.get_database_image_files(db)
        fs_files = self.get_filesystem_image_files()
        
        # Orphaned files are in filesystem but not in database
        orphaned_files = fs_files - db_files
        
        logger.info(f"Found {len(orphaned_files)} orphaned image files")
        return list(orphaned_files)
    
    def delete_orphaned_images(self, orphaned_files: List[str], dry_run: bool = True) -> dict:
        """
        Delete orphaned image files from filesystem.
        
        Args:
            orphaned_files: List of orphaned image filenames
            dry_run: If True, only simulate deletion without actually deleting
            
        Returns:
            Dictionary with deletion results
        """
        results = {
            'deleted_count': 0,
            'failed_count': 0,
            'total_size_freed': 0,
            'deleted_files': [],
            'failed_files': []
        }
        
        if not orphaned_files:
            logger.info("No orphaned images to delete")
            return results
        
        logger.info(f"{'Simulating' if dry_run else 'Starting'} deletion of {len(orphaned_files)} orphaned images")
        
        for filename in orphaned_files:
            try:
                file_path = self.image_dir / filename
                
                if not file_path.exists():
                    logger.warning(f"File {filename} not found, skipping")
                    continue
                
                # Get file size before deletion
                file_size = file_path.stat().st_size
                
                if dry_run:
                    logger.info(f"Would delete: {filename} ({file_size} bytes)")
                    results['deleted_files'].append(filename)
                    results['deleted_count'] += 1
                    results['total_size_freed'] += file_size
                else:
                    file_path.unlink()
                    logger.info(f"Deleted: {filename} ({file_size} bytes)")
                    results['deleted_files'].append(filename)
                    results['deleted_count'] += 1
                    results['total_size_freed'] += file_size
                    
            except Exception as e:
                logger.error(f"Failed to delete {filename}: {e}")
                results['failed_files'].append(filename)
                results['failed_count'] += 1
        
        action = "Would delete" if dry_run else "Deleted"
        logger.info(f"{action} {results['deleted_count']} files, freed {results['total_size_freed']} bytes")
        
        if results['failed_count'] > 0:
            logger.warning(f"Failed to delete {results['failed_count']} files")
        
        return results
    
    def cleanup_orphaned_images(self, dry_run: bool = True) -> dict:
        """
        Complete orphaned image cleanup process.
        
        Args:
            dry_run: If True, only simulate cleanup without actually deleting
            
        Returns:
            Dictionary with cleanup results
        """
        logger.info(f"Starting orphaned image cleanup (dry_run={dry_run})")
        
        try:
            # Get database session
            db = next(get_db())
            
            try:
                # Find orphaned images
                orphaned_files = self.find_orphaned_images(db)
                
                # Delete orphaned images
                results = self.delete_orphaned_images(orphaned_files, dry_run=dry_run)
                
                results['success'] = True
                results['message'] = f"Cleanup completed successfully"
                
                return results
                
            finally:
                db.close()
                
        except Exception as e:
            logger.error(f"Error during orphaned image cleanup: {e}")
            return {
                'success': False,
                'message': f"Cleanup failed: {str(e)}",
                'deleted_count': 0,
                'failed_count': 0,
                'total_size_freed': 0
            }


# Global service instance
image_cleanup_service = ImageCleanupService()


async def scheduled_image_cleanup(interval_hours: int = 24, dry_run: bool = False):
    """
    Run scheduled image cleanup at specified intervals.
    
    Args:
        interval_hours: Hours between cleanup runs
        dry_run: If True, only simulate cleanup
    """
    logger.info(f"Starting scheduled image cleanup (interval: {interval_hours}h, dry_run={dry_run})")
    
    while True:
        try:
            results = image_cleanup_service.cleanup_orphaned_images(dry_run=dry_run)
            
            if results.get('success'):
                logger.info(f"Scheduled cleanup completed: {results}")
            else:
                logger.error(f"Scheduled cleanup failed: {results}")
                
        except Exception as e:
            logger.error(f"Error in scheduled image cleanup: {e}")
        
        # Wait for next cleanup
        await asyncio.sleep(interval_hours * 3600)  # Convert hours to seconds


def cleanup_images_sync(dry_run: bool = True) -> dict:
    """
    Synchronous wrapper for image cleanup.
    
    Args:
        dry_run: If True, only simulate cleanup
        
    Returns:
        Dictionary with cleanup results
    """
    return image_cleanup_service.cleanup_orphaned_images(dry_run=dry_run)