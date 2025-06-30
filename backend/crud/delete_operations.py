"""
Enhanced delete operations supporting soft and hard delete with cascading
"""
import os
from datetime import datetime, timedelta, timezone
from sqlalchemy.orm import Session
from typing import List
from pathlib import Path

from models.product import Product, Image, Size
from enums.delete_mode import DeleteMode
from utils.logger import get_logger
from utils.database import atomic_transaction
from exceptions.base import DatabaseException, ProductException

logger = get_logger(__name__)
IMAGE_DIR = os.getenv("IMAGE_DIR", "./images")


def soft_delete_product(db: Session, product_id: int) -> bool:
    """
    Soft delete a product and all its related data by setting deleted_at timestamp.
    
    Args:
        db: Database session
        product_id: ID of the product to soft delete
        
    Returns:
        True if soft deletion was successful
        
    Raises:
        ProductException: If product not found
        DatabaseException: If database operation fails
    """
    logger.info(f"Soft deleting product with ID: {product_id}")
    
    try:
        with atomic_transaction(db):
            # Get existing product (including already soft-deleted ones)
            product = db.query(Product).filter(Product.id == product_id).first()
            if not product:
                raise ProductException(
                    message="Product not found for soft deletion",
                    details={"product_id": product_id}
                )
            
            # Check if already soft deleted
            if product.deleted_at is not None:
                logger.warning(f"Product {product_id} is already soft deleted at {product.deleted_at}")
                return True
            
            delete_timestamp = datetime.now(timezone.utc)
            
            # Soft delete associated images
            images_updated = db.query(Image).filter(
                Image.product_id == product_id,
                Image.deleted_at.is_(None)
            ).update({Image.deleted_at: delete_timestamp})
            
            # Soft delete associated sizes
            sizes_updated = db.query(Size).filter(
                Size.product_id == product_id,
                Size.deleted_at.is_(None)
            ).update({Size.deleted_at: delete_timestamp})
            
            # Soft delete the product itself
            product.deleted_at = delete_timestamp
            db.flush()
            
            logger.info(f"Successfully soft deleted product ID: {product_id} with {images_updated} images and {sizes_updated} sizes")
            
        return True
        
    except ProductException:
        raise  # Re-raise product exceptions
    except Exception as e:
        logger.error(f"Error soft deleting product {product_id}: {e}")
        raise DatabaseException(
            message="Failed to soft delete product",
            operation="soft_delete_product",
            table="products",
            details={"product_id": product_id},
            original_exception=e
        )


def hard_delete_product(db: Session, product_id: int) -> bool:
    """
    Hard delete a product and all its related data, including physical image files.
    
    Args:
        db: Database session
        product_id: ID of the product to hard delete
        
    Returns:
        True if hard deletion was successful
        
    Raises:
        ProductException: If product not found
        DatabaseException: If database operation fails
    """
    logger.info(f"Hard deleting product with ID: {product_id}")
    
    try:
        with atomic_transaction(db):
            # Get existing product (including soft-deleted ones)
            product = db.query(Product).filter(Product.id == product_id).first()
            if not product:
                raise ProductException(
                    message="Product not found for hard deletion",
                    details={"product_id": product_id}
                )
            
            # Get all associated images (including soft-deleted ones) for file cleanup
            images = db.query(Image).filter(Image.product_id == product_id).all()
            image_files_to_delete = []
            
            for image in images:
                # Collect image file paths for deletion
                logger.debug(f"Checking image URL: {image.url}")
                if image.url and not image.url.startswith('http'):
                    # Local image file
                    image_path = Path(IMAGE_DIR) / image.url
                    logger.debug(f"Looking for image file at: {image_path}")
                    if image_path.exists():
                        image_files_to_delete.append(image_path)
                        logger.debug(f"Added image file for deletion: {image_path}")
                    else:
                        logger.debug(f"Image file not found: {image_path}")
                else:
                    logger.debug(f"Skipping external image URL: {image.url}")
            
            # Delete associated images from database
            images_deleted = db.query(Image).filter(Image.product_id == product_id).delete()
            logger.debug(f"Hard deleted {images_deleted} image records for product {product_id}")
            
            # Delete associated sizes from database
            sizes_deleted = db.query(Size).filter(Size.product_id == product_id).delete()
            logger.debug(f"Hard deleted {sizes_deleted} size records for product {product_id}")
            
            # Delete the product itself from database
            db.delete(product)
            db.flush()
            
            # After successful database deletion, clean up image files
            files_deleted = 0
            for image_path in image_files_to_delete:
                try:
                    image_path.unlink()
                    files_deleted += 1
                    logger.debug(f"Deleted image file: {image_path}")
                except OSError as e:
                    logger.warning(f"Failed to delete image file {image_path}: {e}")
            
            logger.info(f"Successfully hard deleted product ID: {product_id} with {images_deleted} images, {sizes_deleted} sizes, and {files_deleted} image files")
            
        return True
        
    except ProductException:
        raise  # Re-raise product exceptions
    except Exception as e:
        logger.error(f"Error hard deleting product {product_id}: {e}")
        raise DatabaseException(
            message="Failed to hard delete product",
            operation="hard_delete_product",
            table="products",
            details={"product_id": product_id},
            original_exception=e
        )


def delete_product_with_mode(db: Session, product_id: int, delete_mode: DeleteMode = DeleteMode.SOFT) -> bool:
    """
    Delete a product using the specified delete mode.
    
    Args:
        db: Database session
        product_id: ID of the product to delete
        delete_mode: Whether to perform soft or hard delete
        
    Returns:
        True if deletion was successful
        
    Raises:
        ProductException: If product not found
        DatabaseException: If database operation fails
    """
    logger.info(f"Deleting product {product_id} with mode: {delete_mode}")
    
    if delete_mode == DeleteMode.SOFT:
        return soft_delete_product(db, product_id)
    elif delete_mode == DeleteMode.HARD:
        return hard_delete_product(db, product_id)
    else:
        raise ValueError(f"Invalid delete mode: {delete_mode}")


def restore_product(db: Session, product_id: int) -> bool:
    """
    Restore a soft-deleted product and all its related data.
    
    Args:
        db: Database session
        product_id: ID of the product to restore
        
    Returns:
        True if restoration was successful
        
    Raises:
        ProductException: If product not found or not soft deleted
        DatabaseException: If database operation fails
    """
    logger.info(f"Restoring soft-deleted product with ID: {product_id}")
    
    try:
        with atomic_transaction(db):
            # Get soft-deleted product
            product = db.query(Product).filter(
                Product.id == product_id,
                Product.deleted_at.isnot(None)
            ).first()
            
            if not product:
                # Check if product exists but is not soft deleted
                existing_product = db.query(Product).filter(Product.id == product_id).first()
                if existing_product:
                    raise ProductException(
                        message="Product is not soft deleted and cannot be restored",
                        details={"product_id": product_id}
                    )
                else:
                    raise ProductException(
                        message="Product not found for restoration",
                        details={"product_id": product_id}
                    )
            
            # Restore associated images
            images_restored = db.query(Image).filter(
                Image.product_id == product_id,
                Image.deleted_at.isnot(None)
            ).update({Image.deleted_at: None})
            
            # Restore associated sizes
            sizes_restored = db.query(Size).filter(
                Size.product_id == product_id,
                Size.deleted_at.isnot(None)
            ).update({Size.deleted_at: None})
            
            # Restore the product itself
            product.deleted_at = None
            db.flush()
            
            logger.info(f"Successfully restored product ID: {product_id} with {images_restored} images and {sizes_restored} sizes")
            
        return True
        
    except ProductException:
        raise  # Re-raise product exceptions
    except Exception as e:
        logger.error(f"Error restoring product {product_id}: {e}")
        raise DatabaseException(
            message="Failed to restore product",
            operation="restore_product",
            table="products",
            details={"product_id": product_id},
            original_exception=e
        )


def get_deleted_products(db: Session, skip: int = 0, limit: int = 100) -> List[Product]:
    """
    Get a list of soft-deleted products.
    
    Args:
        db: Database session
        skip: Number of records to skip
        limit: Maximum number of records to return
        
    Returns:
        List of soft-deleted products
    """
    logger.debug(f"Fetching deleted products with skip={skip}, limit={limit}")
    
    try:
        products = db.query(Product).filter(
            Product.deleted_at.isnot(None)
        ).offset(skip).limit(limit).all()
        
        logger.debug(f"Retrieved {len(products)} deleted products")
        return products
        
    except Exception as e:
        logger.error(f"Error retrieving deleted products: {e}")
        raise DatabaseException(
            message="Failed to retrieve deleted products list",
            operation="get_deleted_products",
            table="products",
            details={"skip": skip, "limit": limit},
            original_exception=e
        )


def permanently_delete_old_soft_deleted(db: Session, days_old: int = 30) -> int:
    """
    Permanently delete products that have been soft deleted for more than specified days.
    
    Args:
        db: Database session
        days_old: Number of days after which to permanently delete soft-deleted items
        
    Returns:
        Number of products permanently deleted
        
    Raises:
        DatabaseException: If database operation fails
    """
    logger.info(f"Permanently deleting products soft-deleted more than {days_old} days ago")
    
    try:
        cutoff_date = datetime.now(timezone.utc) - timedelta(days=days_old)
        
        # Get products to be permanently deleted
        # Use <= for cutoff to include products deleted exactly at the cutoff time
        products_to_delete = db.query(Product).filter(
            Product.deleted_at.isnot(None),
            Product.deleted_at <= cutoff_date
        ).all()
        
        deleted_count = 0
        for product in products_to_delete:
            try:
                hard_delete_product(db, int(product.id))
                deleted_count += 1
            except Exception as e:
                logger.error(f"Failed to permanently delete product {product.id}: {e}")
                # Continue with other products
        
        logger.info(f"Permanently deleted {deleted_count} old soft-deleted products")
        return deleted_count
        
    except Exception as e:
        logger.error(f"Error permanently deleting old soft-deleted products: {e}")
        raise DatabaseException(
            message="Failed to permanently delete old soft-deleted products",
            operation="permanently_delete_old_soft_deleted",
            table="products",
            details={"days_old": days_old},
            original_exception=e
        )