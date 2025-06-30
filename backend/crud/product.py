from sqlalchemy.orm import Session, joinedload
from sqlalchemy.exc import IntegrityError, OperationalError
from typing import List, Optional, Dict, Any
from models.product import Product, Image, Size
from schemas.product import ProductCreate, ProductUpdate
from utils.logger import get_logger
from utils.database import atomic_transaction, validate_product_constraints, bulk_create_relationships
from exceptions.base import DatabaseException, ValidationException, ProductException

logger = get_logger(__name__)


def get_product_by_url(db: Session, url: str, include_deleted: bool = False) -> Optional[Product]:
    """
    Get a product by its URL.
    
    Args:
        db: Database session
        url: Product URL to search for
        include_deleted: Whether to include soft-deleted products
        
    Returns:
        Product instance if found, None otherwise
    """
    logger.debug(f"Searching for product with URL: {url}")
    query = db.query(Product).filter(Product.product_url == url)
    
    if not include_deleted:
        query = query.filter(Product.deleted_at.is_(None))
    
    product = query.first()
    if product:
        logger.debug(f"Found product with ID: {product.id}")
    else:
        logger.debug(f"No product found for URL: {url}")
    return product


def get_product_by_sku(db: Session, sku: str, include_deleted: bool = False) -> Optional[Product]:
    """
    Get a product by its SKU.
    
    Args:
        db: Database session
        sku: Product SKU to search for
        include_deleted: Whether to include soft-deleted products
        
    Returns:
        Product instance if found, None otherwise
    """
    logger.debug(f"Searching for product with SKU: {sku}")
    query = db.query(Product).options(
        joinedload(Product.images),
        joinedload(Product.sizes)
    ).filter(Product.sku == sku)
    
    if not include_deleted:
        query = query.filter(Product.deleted_at.is_(None))
    
    product = query.first()
    if product:
        logger.debug(f"Found product with ID: {product.id} for SKU: {sku}")
    else:
        logger.debug(f"No product found for SKU: {sku}")
    return product


def find_existing_product(db: Session, url: str, sku: Optional[str] = None, include_deleted: bool = False) -> Dict[str, Any]:
    """
    Find an existing product by URL or SKU.
    
    Args:
        db: Database session
        url: Product URL to search for
        sku: Product SKU to search for (optional)
        include_deleted: Whether to include soft-deleted products
        
    Returns:
        Dict with keys: 'product', 'match_type' ('url', 'sku', or None)
    """
    logger.debug(f"Searching for existing product with URL: {url}, SKU: {sku}")
    
    # First check for URL match
    url_product = get_product_by_url(db, url, include_deleted)
    if url_product:
        return {'product': url_product, 'match_type': 'url'}
    
    # Then check for SKU match if SKU is provided
    if sku:
        sku_product = get_product_by_sku(db, sku, include_deleted)
        if sku_product:
            return {'product': sku_product, 'match_type': 'sku'}
    
    return {'product': None, 'match_type': None}


def compare_product_data(existing_product: Product, new_data: ProductCreate) -> Dict[str, Any]:
    """
    Compare existing product with new data to determine what has changed.
    
    Args:
        existing_product: The existing product from database
        new_data: New product data from scraping
        
    Returns:
        Dict with keys: 'has_changes', 'field_changes', 'image_changes', 'size_changes'
    """
    logger.debug(f"Comparing product data for product ID: {existing_product.id}")
    
    field_changes = {}
    has_changes = False
    
    # Define fields to compare (excluding relationship fields)
    compare_fields = [
        'name', 'price', 'currency', 'availability', 
        'color', 'composition', 'item', 'comment'
    ]
    
    # Compare basic fields
    for field in compare_fields:
        existing_value = getattr(existing_product, field)
        new_value = getattr(new_data, field)
        
        # Handle None values and normalize strings
        if existing_value != new_value:
            # Special handling for strings - normalize whitespace
            if isinstance(existing_value, str) and isinstance(new_value, str):
                if existing_value.strip() != new_value.strip():
                    field_changes[field] = {
                        'old': existing_value,
                        'new': new_value
                    }
                    has_changes = True
            # Handle numeric and None values
            elif existing_value != new_value:
                field_changes[field] = {
                    'old': existing_value,
                    'new': new_value
                }
                has_changes = True
    
    # Compare images using hash-based comparison
    # First, get existing image hashes and URLs
    existing_image_hashes = {img.file_hash for img in existing_product.images if not img.deleted_at and img.file_hash}
    existing_image_urls = {img.url for img in existing_product.images if not img.deleted_at}
    
    # For new images, we need to check what we have
    new_image_urls = set(new_data.all_image_urls) if new_data.all_image_urls else set()
    
    # Note: At this point, new_data.all_image_urls might contain hashes if images were downloaded
    # or URLs if they haven't been downloaded yet. We'll handle this in the update function.
    
    image_changes = {
        'to_add': new_image_urls - existing_image_urls,
        'to_remove': existing_image_urls - new_image_urls,
        'existing': existing_image_urls & new_image_urls,
        'existing_hashes': existing_image_hashes
    }
    
    if image_changes['to_add'] or image_changes['to_remove']:
        has_changes = True
    
    # Compare sizes
    existing_size_names = {size.name for size in existing_product.sizes if not size.deleted_at}
    new_size_names = set(new_data.available_sizes) if new_data.available_sizes else set()
    
    size_changes = {
        'to_add': new_size_names - existing_size_names,
        'to_remove': existing_size_names - new_size_names,
        'existing': existing_size_names & new_size_names
    }
    
    if size_changes['to_add'] or size_changes['to_remove']:
        has_changes = True
    
    logger.debug(f"Product comparison complete. Has changes: {has_changes}")
    
    return {
        'has_changes': has_changes,
        'field_changes': field_changes,
        'image_changes': image_changes,
        'size_changes': size_changes
    }


def create_product(db: Session, product: ProductCreate, downloaded_images_metadata: Optional[List[Dict[str, Any]]] = None) -> Product:
    """
    Create a new product with images and sizes in a single atomic transaction.
    
    Args:
        db: Database session
        product: Product data to create
        downloaded_images_metadata: List of downloaded image metadata (if available)
        
    Returns:
        Created product with relationships loaded
        
    Raises:
        ValidationException: If product data validation fails
        DatabaseException: If database operation fails
        ProductException: If product creation logic fails
    """
    logger.info(f"Creating product: {product.name} ({product.product_url})")
    
    try:
        # Validate input data before attempting database operations
        product_dict = product.model_dump()
        validate_product_constraints(product_dict)
        
    except ValueError as e:
        raise ValidationException(
            message=str(e),
            details={"product_url": str(product.product_url)},
            original_exception=e
        )
    
    try:
        # Use atomic transaction for consistency
        with atomic_transaction(db):
            # Create the main product record
            db_product = Product(
                product_url=str(product.product_url),
                name=product.name,
                sku=product.sku,
                price=product.price,
                currency=product.currency,
                availability=product.availability,
                color=product.color,
                composition=product.composition,
                item=product.item,
                comment=product.comment,
            )

            db.add(db_product)
            # Flush to get the ID without committing the transaction
            db.flush()
            logger.debug(f"Created product with ID: {db_product.id}")

            # Add images using bulk creation for better performance
            if product.all_image_urls:
                logger.info(f"Adding {len(product.all_image_urls)} images to product ID: {db_product.id}")
                
                if downloaded_images_metadata:
                    # Pass the full metadata objects directly instead of just image IDs
                    bulk_create_relationships(db, int(db_product.id), downloaded_images_metadata, Image, 'url')
                else:
                    # Fallback for existing behavior
                    bulk_create_relationships(db, int(db_product.id), product.all_image_urls, Image, 'url')

            # Add sizes using improved size handling
            if product.size_combinations:
                # Handle dual size selectors with combinations
                logger.info(f"Adding size combinations to product ID: {db_product.id}")
                create_size_combinations_new(db, int(db_product.id), product.size_combinations)
            elif product.available_sizes:
                # Handle simple sizes
                logger.info(f"Adding {len(product.available_sizes)} simple sizes to product ID: {db_product.id}")
                create_simple_sizes(db, int(db_product.id), product.available_sizes)

            # Transaction will be committed by the context manager
            logger.debug("All product data prepared for atomic commit")

    except IntegrityError as e:
        error_msg = str(e.orig) if hasattr(e, 'orig') else str(e)
        
        # Determine specific constraint violation
        if "UNIQUE constraint failed: products.product_url" in error_msg:
            raise ProductException(
                message="Product with this URL already exists",
                product_url=str(product.product_url),
                details={"constraint": "product_url_unique"},
                original_exception=e
            )
        elif "UNIQUE constraint failed: products.sku" in error_msg:
            raise ProductException(
                message="Product with this SKU already exists",
                product_url=str(product.product_url),
                details={"constraint": "sku_unique", "sku": product.sku},
                original_exception=e
            )
        elif "UNIQUE constraint failed: images.url" in error_msg:
            raise DatabaseException(
                message="Duplicate image URL detected",
                operation="create_product",
                table="images",
                details={"product_url": str(product.product_url)},
                original_exception=e
            )
        else:
            raise DatabaseException(
                message="Database constraint violation during product creation",
                operation="create_product",
                table="products",
                details={"product_url": str(product.product_url), "error": error_msg},
                original_exception=e
            )
    
    except OperationalError as e:
        raise DatabaseException(
            message="Database operational error during product creation",
            operation="create_product",
            details={"product_url": str(product.product_url)},
            original_exception=e
        )
    
    except Exception as e:
        raise ProductException(
            message="Unexpected error during product creation",
            product_url=str(product.product_url),
            details={"error_type": type(e).__name__},
            original_exception=e
        )

    try:
        # After successful commit, load the complete product with relationships
        db_product = db.query(Product).options(
            joinedload(Product.images), 
            joinedload(Product.sizes)
        ).filter(Product.id == db_product.id).first()
        
        if not db_product:
            raise ProductException(
                message="Product was created but could not be retrieved",
                details={"product_url": str(product.product_url)}
            )

        logger.info(f"Successfully created product ID: {db_product.id} with {len(db_product.images)} images and {len(db_product.sizes)} sizes")
        return db_product
        
    except Exception as e:
        raise DatabaseException(
            message="Failed to retrieve created product",
            operation="get_product",
            table="products",
            details={"product_url": str(product.product_url)},
            original_exception=e
        )


def create_size_combinations_new(db: Session, product_id: int, size_combinations_data: Dict[str, Any]) -> None:
    """
    Create size combinations from browser extension data using new structure.
    
    Args:
        db: Database session
        product_id: ID of the product
        size_combinations_data: Dict with size1_type, size2_type, and combinations
    """
    from models.product import Size
    
    logger.debug(f"Creating size combinations for product {product_id}: {size_combinations_data}")
    
    # Extract data from the combination structure
    size1_type = size_combinations_data.get('size1_type', 'size1')
    size2_type = size_combinations_data.get('size2_type', 'size2')
    combinations = size_combinations_data.get('combinations', {})
    
    if not combinations:
        logger.warning(f"No combinations data found for product {product_id}")
        return
    
    # Create a single Size record to store all combinations
    size_record = Size(
        product_id=product_id,
        size_type="combination",
        size1_type=size1_type,
        size2_type=size2_type,
        combination_data=combinations
    )
    
    db.add(size_record)
    logger.info(f"Created size combination record for product {product_id} with {len(combinations)} size1 options")


def create_simple_sizes(db: Session, product_id: int, available_sizes: List[str]) -> None:
    """
    Create simple size records from available sizes list.
    
    Args:
        db: Database session
        product_id: ID of the product
        available_sizes: List of size strings (e.g., ["S", "M", "L"])
    """
    from models.product import Size
    
    logger.debug(f"Creating simple sizes for product {product_id}: {available_sizes}")
    
    if not available_sizes:
        logger.warning(f"No available sizes found for product {product_id}")
        return
    
    # Create a Size record for each simple size
    for size_value in available_sizes:
        size_record = Size(
            product_id=product_id,
            size_type="simple",
            size_value=size_value
        )
        db.add(size_record)
    
    logger.info(f"Created {len(available_sizes)} simple size records for product {product_id}")


def create_size_combinations(db: Session, product_id: int, size_combinations_data: Dict[str, Any]) -> None:
    """
    Legacy function - kept for backward compatibility.
    """
    return create_size_combinations_new(db, product_id, size_combinations_data)


def filter_duplicate_images_by_hash(new_images_metadata: List[Dict[str, Any]], existing_hashes: set[str]) -> List[Dict[str, Any]]:
    """
    Filter out images that already exist based on their hash.
    
    Args:
        new_images_metadata: List of image metadata dicts with 'file_hash' and other info
        existing_hashes: Set of existing image hashes
        
    Returns:
        List of unique image metadata that don't already exist
    """
    unique_images = []
    for img_meta in new_images_metadata:
        if isinstance(img_meta, dict) and img_meta.get('file_hash'):
            if img_meta['file_hash'] not in existing_hashes:
                unique_images.append(img_meta)
            else:
                logger.debug(f"Skipping duplicate image with hash: {img_meta['file_hash'][:16]}...")
        else:
            # If no hash available, include it (might be a URL that needs downloading)
            unique_images.append(img_meta)
    
    return unique_images


async def update_existing_product_with_changes(db: Session, existing_product: Product, new_data: ProductCreate, changes: Dict[str, Any], download_new_images: bool = True, downloaded_images_metadata: Optional[List[Dict[str, Any]]] = None) -> Product:
    """
    Update an existing product with new data based on detected changes.
    
    Args:
        db: Database session
        existing_product: The existing product to update
        new_data: New product data from scraping
        changes: Changes detected by compare_product_data
        download_new_images: Whether to download new images
        downloaded_images_metadata: List of downloaded image metadata (if images were already downloaded)
        
    Returns:
        Updated product instance and summary of changes made
        
    Raises:
        DatabaseException: If update fails
    """
    from services.image_downloader import download_images
    from utils.database import bulk_create_relationships
    
    logger.info(f"Updating existing product ID: {existing_product.id} with detected changes")
    
    try:
        with atomic_transaction(db):
            # Update basic fields
            if changes['field_changes']:
                for field, change in changes['field_changes'].items():
                    setattr(existing_product, field, change['new'])
                    logger.debug(f"Updated field {field}: {change['old']} -> {change['new']}")
            
            # Handle image changes with duplicate detection
            images_added = []
            if changes['image_changes']['to_add'] and download_new_images:
                existing_hashes = changes['image_changes'].get('existing_hashes', set())
                
                # If we already have downloaded images metadata, use it
                if downloaded_images_metadata:
                    # Filter out duplicates by hash
                    unique_images_metadata = filter_duplicate_images_by_hash(downloaded_images_metadata, existing_hashes)
                    
                    if unique_images_metadata:
                        # Pass the metadata objects directly
                        bulk_create_relationships(db, existing_product.id, unique_images_metadata, Image, 'url')
                        images_added = [img['image_id'] for img in unique_images_metadata]
                        logger.info(f"Added {len(images_added)} unique new images to product {existing_product.id}")
                    else:
                        logger.info(f"No unique images to add to product {existing_product.id} - all were duplicates")
                else:
                    # Download new images and filter duplicates
                    new_image_urls = list(changes['image_changes']['to_add'])
                    logger.info(f"Downloading {len(new_image_urls)} new images for product {existing_product.id}")
                    
                    downloaded_results = await download_images(new_image_urls)
                    if downloaded_results:
                        # Filter out duplicates by hash
                        unique_images_metadata = filter_duplicate_images_by_hash(downloaded_results, existing_hashes)
                        
                        if unique_images_metadata:
                            # Pass the metadata objects directly
                            bulk_create_relationships(db, existing_product.id, unique_images_metadata, Image, 'url')
                            images_added = [img['image_id'] for img in unique_images_metadata]
                            logger.info(f"Added {len(images_added)} unique new images to product {existing_product.id}")
                        else:
                            logger.info(f"No unique images to add to product {existing_product.id} - all were duplicates")
            
            # Handle size changes
            sizes_added = []
            if changes['size_changes']['to_add']:
                new_sizes = list(changes['size_changes']['to_add'])
                bulk_create_relationships(db, existing_product.id, new_sizes, Size, 'name')
                sizes_added = new_sizes
                logger.info(f"Added {len(sizes_added)} new sizes to product {existing_product.id}")
            
            # Note: We don't remove existing images or sizes to preserve data
            # Only add new ones that weren't present before
            
            db.flush()
            
    except Exception as e:
        logger.error(f"Failed to update product {existing_product.id}: {e}")
        raise DatabaseException(
            message="Failed to update existing product",
            operation="update_existing_product",
            table="products",
            details={"product_id": existing_product.id},
            original_exception=e
        )
    
    try:
        # Return updated product with relationships
        updated_product = db.query(Product).options(
            joinedload(Product.images),
            joinedload(Product.sizes)
        ).filter(Product.id == existing_product.id).first()
        
        # Create summary of changes made
        update_summary = {
            'fields_updated': list(changes['field_changes'].keys()),
            'images_added': len(images_added),
            'sizes_added': len(sizes_added),
            'total_images': len([img for img in updated_product.images if not img.deleted_at]),
            'total_sizes': len([size for size in updated_product.sizes if not size.deleted_at])
        }
        
        logger.info(f"Successfully updated product {existing_product.id}. Summary: {update_summary}")
        
        return updated_product, update_summary
        
    except Exception as e:
        raise DatabaseException(
            message="Failed to retrieve updated product",
            operation="get_updated_product",
            table="products",
            details={"product_id": existing_product.id},
            original_exception=e
        )


def get_product_by_id(db: Session, product_id: int, include_deleted: bool = False) -> Optional[Product]:
    """
    Get a product by its ID with all relationships loaded.
    
    Args:
        db: Database session
        product_id: Product ID to search for
        include_deleted: Whether to include soft-deleted products
        
    Returns:
        Product instance if found, None otherwise
    """
    logger.debug(f"Searching for product with ID: {product_id}")
    
    try:
        query = db.query(Product).options(
            joinedload(Product.images),
            joinedload(Product.sizes)
        ).filter(Product.id == product_id)
        
        if not include_deleted:
            query = query.filter(Product.deleted_at.is_(None))
        
        product = query.first()
        
        if product:
            logger.debug(f"Found product: {product.name}")
        else:
            logger.debug(f"No product found for ID: {product_id}")
        
        return product
        
    except Exception as e:
        logger.error(f"Error retrieving product by ID {product_id}: {e}")
        raise DatabaseException(
            message="Failed to retrieve product by ID",
            operation="get_product_by_id",
            table="products",
            details={"product_id": product_id},
            original_exception=e
        )


def get_products(
    db: Session, 
    skip: int = 0, 
    limit: int = 100,
    load_relationships: bool = True,
    include_deleted: bool = False
) -> List[Product]:
    """
    Get a list of products with pagination.
    
    Args:
        db: Database session
        skip: Number of records to skip
        limit: Maximum number of records to return
        load_relationships: Whether to load images and sizes
        include_deleted: Whether to include soft-deleted products
        
    Returns:
        List of products
    """
    logger.debug(f"Fetching products with skip={skip}, limit={limit}")
    
    try:
        query = db.query(Product)
        
        if not include_deleted:
            query = query.filter(Product.deleted_at.is_(None))
        
        if load_relationships:
            query = query.options(
                joinedload(Product.images),
                joinedload(Product.sizes)
            )
        
        products = query.offset(skip).limit(limit).all()
        logger.debug(f"Retrieved {len(products)} products")
        
        return products
        
    except Exception as e:
        logger.error(f"Error retrieving products: {e}")
        raise DatabaseException(
            message="Failed to retrieve products list",
            operation="get_products",
            table="products",
            details={"skip": skip, "limit": limit},
            original_exception=e
        )


def update_product(db: Session, product_id: int, product_update: ProductUpdate) -> Product:
    """
    Update an existing product.
    
    Args:
        db: Database session
        product_id: ID of the product to update
        product_update: Product data to update
        
    Returns:
        Updated product instance
        
    Raises:
        ProductException: If product not found or update fails
        DatabaseException: If database operation fails
    """
    logger.info(f"Updating product with ID: {product_id}")
    
    try:
        with atomic_transaction(db):
            # Get existing product
            product = db.query(Product).filter(Product.id == product_id).first()
            if not product:
                raise ProductException(
                    message="Product not found for update",
                    details={"product_id": product_id}
                )
            
            # Update fields that are provided (not None)
            update_data = product_update.model_dump(exclude_unset=True, exclude_none=True)
            
            # Validate the update data
            if update_data:
                # Convert URL to string if present
                if 'product_url' in update_data:
                    update_data['product_url'] = str(update_data['product_url'])
                
                # Validate updated data
                merged_data = {
                    'product_url': update_data.get('product_url', product.product_url),
                    'price': update_data.get('price', product.price)
                }
                validate_product_constraints(merged_data)
                
                # Apply updates
                for field, value in update_data.items():
                    setattr(product, field, value)
                
                db.flush()
                logger.debug(f"Updated product fields: {list(update_data.keys())}")
            
    except ValidationException:
        raise  # Re-raise validation exceptions
    except IntegrityError as e:
        error_msg = str(e.orig) if hasattr(e, 'orig') else str(e)
        
        if "UNIQUE constraint failed: products.product_url" in error_msg:
            raise ProductException(
                message="Product URL already exists",
                details={"product_id": product_id, "constraint": "product_url_unique"},
                original_exception=e
            )
        elif "UNIQUE constraint failed: products.sku" in error_msg:
            raise ProductException(
                message="Product SKU already exists",
                details={"product_id": product_id, "constraint": "sku_unique"},
                original_exception=e
            )
        else:
            raise DatabaseException(
                message="Database constraint violation during product update",
                operation="update_product",
                table="products",
                details={"product_id": product_id, "error": error_msg},
                original_exception=e
            )
    except Exception as e:
        raise DatabaseException(
            message="Failed to update product",
            operation="update_product",
            table="products",
            details={"product_id": product_id},
            original_exception=e
        )
    
    try:
        # Return updated product with relationships
        updated_product = db.query(Product).options(
            joinedload(Product.images),
            joinedload(Product.sizes)
        ).filter(Product.id == product_id).first()
        
        logger.info(f"Successfully updated product ID: {product_id}")
        return updated_product
        
    except Exception as e:
        raise DatabaseException(
            message="Failed to retrieve updated product",
            operation="get_product",
            table="products",
            details={"product_id": product_id},
            original_exception=e
        )


def delete_product(db: Session, product_id: int) -> bool:
    """
    Delete a product using soft delete (default behavior for backward compatibility).
    
    Args:
        db: Database session
        product_id: ID of the product to delete
        
    Returns:
        True if deletion was successful
        
    Raises:
        ProductException: If product not found
        DatabaseException: If database operation fails
    """
    from crud.delete_operations import soft_delete_product
    return soft_delete_product(db, product_id)


def get_product_count(db: Session, include_deleted: bool = False) -> int:
    """
    Get the total count of products.
    
    Args:
        db: Database session
        include_deleted: Whether to include soft-deleted products
        
    Returns:
        Total number of products
    """
    try:
        query = db.query(Product)
        
        if not include_deleted:
            query = query.filter(Product.deleted_at.is_(None))
        
        count = query.count()
        logger.debug(f"Total product count: {count}")
        return count
    except Exception as e:
        logger.error(f"Error getting product count: {e}")
        raise DatabaseException(
            message="Failed to get product count",
            operation="get_product_count",
            table="products",
            original_exception=e
        )
