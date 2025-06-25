import httpx
import os
import uuid
from typing import List
from utils.logger import get_logger
from exceptions.base import ImageDownloadException, ExternalServiceException

logger = get_logger(__name__)
IMAGE_DIR = os.getenv("IMAGE_DIR", "./images")


async def download_images(image_urls: List[str]) -> List[str]:
    """
    Download images from URLs and save them locally.
    
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

    saved_image_ids = []
    failed_downloads = []
    logger.info(f"Starting download of {len(image_urls)} images")
    
    try:
        async with httpx.AsyncClient(timeout=httpx.Timeout(30.0)) as client:
            for i, url in enumerate(image_urls, 1):
                try:
                    logger.debug(f"Downloading image {i}/{len(image_urls)}: {url}")
                    response = await client.get(str(url))
                    response.raise_for_status()
                    
                    # Validate content type
                    content_type = response.headers.get('content-type', '')
                    if not content_type.startswith('image/'):
                        logger.warning(f"Invalid content type for {url}: {content_type}")
                        failed_downloads.append({
                            "url": url,
                            "error": "Invalid content type",
                            "content_type": content_type
                        })
                        continue
                    
                    # Validate content size (max 10MB)
                    content_length = len(response.content)
                    if content_length > 10 * 1024 * 1024:
                        logger.warning(f"Image too large for {url}: {content_length} bytes")
                        failed_downloads.append({
                            "url": url,
                            "error": "Image too large",
                            "size_bytes": content_length
                        })
                        continue
                    
                    image_id = f"{uuid.uuid4()}.jpg"
                    file_path = os.path.join(IMAGE_DIR, image_id)
                    
                    with open(file_path, "wb") as f:
                        f.write(response.content)
                    
                    saved_image_ids.append(image_id)
                    logger.info(f"Successfully downloaded image {i}/{len(image_urls)}: {url} -> {image_id}")
                    
                except httpx.HTTPStatusError as e:
                    error_msg = f"HTTP {e.response.status_code} error downloading image from {url}"
                    logger.error(error_msg)
                    failed_downloads.append({
                        "url": url,
                        "error": "HTTP error",
                        "status_code": e.response.status_code,
                        "details": str(e)
                    })
                    
                except httpx.RequestError as e:
                    error_msg = f"Request error downloading image from {url}: {e}"
                    logger.error(error_msg)
                    failed_downloads.append({
                        "url": url,
                        "error": "Request error",
                        "details": str(e)
                    })
                    
                except OSError as e:
                    error_msg = f"File system error saving image from {url}: {e}"
                    logger.error(error_msg)
                    failed_downloads.append({
                        "url": url,
                        "error": "File system error",
                        "details": str(e)
                    })
                    
                except Exception as e:
                    error_msg = f"Unexpected error downloading image from {url}: {e}"
                    logger.error(error_msg)
                    failed_downloads.append({
                        "url": url,
                        "error": "Unexpected error",
                        "details": str(e)
                    })
    
    except Exception as e:
        # Critical error with the HTTP client
        raise ExternalServiceException(
            message="Failed to initialize HTTP client for image downloads",
            service="httpx_client",
            details={"error": str(e)},
            original_exception=e
        )
    
    success_count = len(saved_image_ids)
    total_count = len(image_urls)
    failure_count = len(failed_downloads)
    
    logger.info(f"Image download completed: {success_count}/{total_count} successful, {failure_count} failed")
    
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
