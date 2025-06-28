import time
from contextlib import contextmanager
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError, OperationalError
from utils.logger import get_logger

logger = get_logger(__name__)


@contextmanager
def atomic_transaction(db: Session):
    """
    Simple context manager for atomic database transactions.
    
    Args:
        db: Database session
        
    Yields:
        Database session
        
    Raises:
        Exception: If transaction fails
    """
    try:
        # Yield the session for the transaction
        yield db
        
        # If we get here without exception, commit the transaction
        db.commit()
        logger.debug("Transaction committed successfully")
        
    except IntegrityError as e:
        # Integrity constraint violations
        logger.error(f"Database integrity error: {e}")
        db.rollback()
        raise
        
    except OperationalError as e:
        # Database operational errors
        logger.error(f"Database operational error: {e}")
        db.rollback()
        raise
        
    except Exception as e:
        # Any other exception - rollback and re-raise
        logger.error(f"Unexpected database error: {e}")
        db.rollback()
        raise


def execute_with_retry(func, max_retries: int = 3, *args, **kwargs):
    """
    Execute a function with retry logic for deadlock handling.
    
    Args:
        func: Function to execute
        max_retries: Maximum number of retry attempts
        *args: Arguments to pass to the function
        **kwargs: Keyword arguments to pass to the function
        
    Returns:
        Function result
        
    Raises:
        Exception: If function fails after all retries
    """
    retry_count = 0
    
    while retry_count <= max_retries:
        try:
            return func(*args, **kwargs)
            
        except OperationalError as e:
            # Handle deadlocks and lock timeout errors
            if "deadlock" in str(e).lower() or "lock wait timeout" in str(e).lower():
                retry_count += 1
                
                if retry_count <= max_retries:
                    wait_time = 0.1 * (2 ** retry_count)  # Exponential backoff
                    logger.warning(f"Database deadlock detected, retry {retry_count}/{max_retries} after {wait_time}s: {e}")
                    time.sleep(wait_time)
                    continue
                else:
                    logger.error(f"Function failed after {max_retries} retries due to deadlock: {e}")
                    raise
            else:
                # Other operational errors - don't retry
                raise


def validate_product_constraints(product_data: dict) -> None:
    """
    Validate product data before database insertion.
    
    Args:
        product_data: Product data dictionary
        
    Raises:
        ValueError: If validation fails
    """
    # Check required fields
    required_fields = ['product_url']
    for field in required_fields:
        if not product_data.get(field):
            raise ValueError(f"Required field '{field}' is missing or empty")
    
    # Validate URL format (basic check)
    product_url = str(product_data['product_url'])
    if not product_url.startswith(('http://', 'https://')):
        raise ValueError(f"Invalid product URL format: {product_url}")
    
    # Validate price if provided
    price = product_data.get('price')
    if price is not None and price < 0:
        raise ValueError(f"Price cannot be negative: {price}")
    
    logger.debug(f"Product data validation passed for URL: {product_url}")


def bulk_create_relationships(db: Session, parent_id: int, relationships: list, relationship_class, field_name: str, **kwargs):
    """
    Efficiently create multiple relationship records.
    
    Args:
        db: Database session
        parent_id: ID of the parent record
        relationships: List of relationship data
        relationship_class: SQLAlchemy model class for relationships
        field_name: Name of the field containing the relationship data
        **kwargs: Additional data for relationships (e.g., image_metadata for Images)
    """
    if not relationships:
        return
    
    logger.debug(f"Bulk creating {len(relationships)} {relationship_class.__name__} records")
    
    # Create all relationship objects
    relationship_objects = []
    image_metadata = kwargs.get('image_metadata', {})
    
    for item in relationships:
        if relationship_class.__name__ == 'Image':
            # For images, item could be just URL string or dict with metadata
            if isinstance(item, dict):
                # Item is a metadata dict from download_images
                url = item.get('image_id')  # Use image_id as the URL for database storage
                file_hash = item.get('file_hash')
                file_size = item.get('size_bytes')
            else:
                url = str(item)
                # Look for metadata by URL if available
                metadata = image_metadata.get(url, {})
                file_hash = metadata.get('file_hash')
                file_size = metadata.get('size_bytes')
            
            obj = relationship_class(
                url=url, 
                product_id=parent_id,
                file_hash=file_hash,
                file_size=file_size
            )
        elif relationship_class.__name__ == 'Size':
            obj = relationship_class(name=str(item), product_id=parent_id)
        else:
            raise ValueError(f"Unsupported relationship class: {relationship_class.__name__}")
        
        relationship_objects.append(obj)
    
    # Add all objects to session at once
    db.add_all(relationship_objects)
    logger.debug(f"Added {len(relationship_objects)} {relationship_class.__name__} objects to session")