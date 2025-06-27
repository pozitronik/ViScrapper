import asyncio
import httpx
import os
import uuid
from typing import List, Dict, Any
from utils.logger import get_logger
from exceptions.base import ImageDownloadException, ExternalServiceException

logger = get_logger(__name__)
IMAGE_DIR = os.getenv("IMAGE_DIR", "./images")

# Configuration constants
MAX_CONCURRENT_DOWNLOADS = int(os.getenv("MAX_CONCURRENT_DOWNLOADS", "5"))
REQUEST_TIMEOUT = float(os.getenv("REQUEST_TIMEOUT", "30.0"))
MAX_IMAGE_SIZE = int(os.getenv("MAX_IMAGE_SIZE", str(10 * 1024 * 1024)))  # 10MB
RETRY_ATTEMPTS = int(os.getenv("RETRY_ATTEMPTS", "2"))
RETRY_DELAY = float(os.getenv("RETRY_DELAY", "1.0"))


async def download_single_image(
    client: httpx.AsyncClient,
    url: str,
    semaphore: asyncio.Semaphore,
    index: int = 0,
    total: int = 0
) -> Dict[str, Any]:
    """
    Download a single image with retry logic and proper error handling.
    
    Args:
        client: HTTP client to use for download
        url: URL of the image to download
        semaphore: Semaphore to control concurrency
        index: Index of this download (for logging)
        total: Total number of downloads (for logging)
        
    Returns:
        Dict containing either success data or error information
    """
    async with semaphore:  # Control concurrency
        for attempt in range(RETRY_ATTEMPTS + 1):
            try:
                if attempt > 0:
                    logger.debug(f"Retry attempt {attempt} for image {index}/{total}: {url}")
                    await asyncio.sleep(RETRY_DELAY * attempt)  # Exponential backoff
                
                logger.debug(f"Downloading image {index}/{total}: {url}")
                response = await client.get(str(url))
                response.raise_for_status()
                
                # Validate content type
                content_type = response.headers.get('content-type', '')
                if not content_type.startswith('image/'):
                    return {
                        "success": False,
                        "url": url,
                        "error": "Invalid content type",
                        "content_type": content_type
                    }
                
                # Validate content size
                content_length = len(response.content)
                if content_length > MAX_IMAGE_SIZE:
                    return {
                        "success": False,
                        "url": url,
                        "error": "Image too large",
                        "size_bytes": content_length
                    }
                
                # Generate unique filename
                image_id = f"{uuid.uuid4()}.jpg"
                file_path = os.path.join(IMAGE_DIR, image_id)
                
                # Save file
                with open(file_path, "wb") as f:
                    f.write(response.content)
                
                logger.info(f"Successfully downloaded image {index}/{total}: {url} -> {image_id}")
                return {
                    "success": True,
                    "url": url,
                    "image_id": image_id,
                    "size_bytes": content_length,
                    "content_type": content_type
                }
                
            except httpx.HTTPStatusError as e:
                error_details = {
                    "success": False,
                    "url": url,
                    "error": "HTTP error",
                    "status_code": e.response.status_code,
                    "details": str(e)
                }
                
                # Don't retry on client errors (4xx), but retry on server errors (5xx)
                if e.response.status_code < 500 or attempt == RETRY_ATTEMPTS:
                    logger.error(f"HTTP {e.response.status_code} error downloading image from {url}")
                    return error_details
                    
            except httpx.RequestError as e:
                error_details = {
                    "success": False,
                    "url": url,
                    "error": "Request error",
                    "details": str(e)
                }
                
                # Retry on network errors
                if attempt == RETRY_ATTEMPTS:
                    logger.error(f"Request error downloading image from {url}: {e}")
                    return error_details
                    
            except OSError as e:
                logger.error(f"File system error saving image from {url}: {e}")
                return {
                    "success": False,
                    "url": url,
                    "error": "File system error",
                    "details": str(e)
                }
                
            except Exception as e:
                logger.error(f"Unexpected error downloading image from {url}: {e}")
                return {
                    "success": False,
                    "url": url,
                    "error": "Unexpected error",
                    "details": str(e)
                }
        
        # Should never reach here, but just in case
        return {
            "success": False,
            "url": url,
            "error": "Max retries exceeded",
            "attempts": RETRY_ATTEMPTS + 1
        }


async def download_images(image_urls: List[str]) -> List[str]:
    """
    Download images from URLs in parallel and save them locally.
    
    Args:
        image_urls: List of image URLs to download
        
    Returns:
        List of local image IDs (filenames) for successfully downloaded images
        
    Raises:
        ExternalServiceException: If directory creation fails
        ImageDownloadException: If critical download errors occur
    """
    if not image_urls:
        logger.info("No images to download")
        return []
    
    # Ensure image directory exists
    try:
        if not os.path.exists(IMAGE_DIR):
            os.makedirs(IMAGE_DIR)
            logger.info(f"Created image directory: {IMAGE_DIR}")
    except OSError as e:
        raise ExternalServiceException(
            message=f"Failed to create image directory: {IMAGE_DIR}",
            service="file_system",
            details={"directory": IMAGE_DIR, "error": str(e)},
            original_exception=e
        )

    total_count = len(image_urls)
    logger.info(f"Starting parallel download of {total_count} images (max {MAX_CONCURRENT_DOWNLOADS} concurrent)")
    
    # Create semaphore to control concurrency
    semaphore = asyncio.Semaphore(MAX_CONCURRENT_DOWNLOADS)
    
    try:
        async with httpx.AsyncClient(timeout=httpx.Timeout(REQUEST_TIMEOUT)) as client:
            # Create download tasks for all images
            download_tasks = [
                download_single_image(client, url, semaphore, i + 1, total_count)
                for i, url in enumerate(image_urls)
            ]
            
            # Execute all downloads in parallel
            logger.debug(f"Executing {len(download_tasks)} download tasks in parallel")
            results = await asyncio.gather(*download_tasks, return_exceptions=True)
            
    except Exception as e:
        # Critical error with the HTTP client setup
        raise ExternalServiceException(
            message="Failed to initialize HTTP client for image downloads",
            service="httpx_client",
            details={"error": str(e)},
            original_exception=e
        )
    
    # Process results
    saved_image_ids = []
    failed_downloads = []
    
    for i, result in enumerate(results):
        if isinstance(result, Exception):
            # Handle exceptions that were caught by gather
            logger.error(f"Download task failed with exception: {result}")
            failed_downloads.append({
                "url": image_urls[i],
                "error": "Task exception",
                "details": str(result)
            })
        elif isinstance(result, dict):
            if result.get("success"):
                saved_image_ids.append(result["image_id"])
            else:
                failed_downloads.append({
                    "url": result["url"],
                    "error": result["error"],
                    **{k: v for k, v in result.items() if k not in ["success", "url", "error"]}
                })
        else:
            # Unexpected result format
            logger.error(f"Unexpected result format: {result}")
            failed_downloads.append({
                "url": image_urls[i] if i < len(image_urls) else "unknown",
                "error": "Unexpected result format",
                "details": str(result)
            })
    
    success_count = len(saved_image_ids)
    failure_count = len(failed_downloads)
    
    logger.info(f"Parallel image download completed: {success_count}/{total_count} successful, {failure_count} failed")
    
    # Log failed downloads for debugging
    if failed_downloads:
        logger.warning(f"Failed to download {failure_count} images: {failed_downloads}")
    
    # If no images were downloaded successfully and we tried multiple images, this might indicate a serious issue
    # For single image downloads, return empty list instead of raising exception
    if success_count == 0 and total_count > 1:
        raise ImageDownloadException(
            message="Failed to download any images",
            details={
                "total_attempted": total_count,
                "failed_downloads": failed_downloads
            }
        )
    
    return saved_image_ids
