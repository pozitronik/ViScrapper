import httpx
import os
import uuid
from typing import List
from utils.logger import get_logger

logger = get_logger(__name__)
IMAGE_DIR = os.getenv("IMAGE_DIR", "./images")


async def download_images(image_urls: List[str]) -> List[str]:
    """
    Download images from URLs and save them locally.
    
    Args:
        image_urls: List of image URLs to download
        
    Returns:
        List of local image IDs (filenames) for successfully downloaded images
    """
    if not os.path.exists(IMAGE_DIR):
        os.makedirs(IMAGE_DIR)
        logger.info(f"Created image directory: {IMAGE_DIR}")

    saved_image_ids = []
    logger.info(f"Starting download of {len(image_urls)} images")
    
    async with httpx.AsyncClient() as client:
        for i, url in enumerate(image_urls, 1):
            try:
                logger.debug(f"Downloading image {i}/{len(image_urls)}: {url}")
                response = await client.get(str(url))
                response.raise_for_status()
                
                image_id = f"{uuid.uuid4()}.jpg"
                file_path = os.path.join(IMAGE_DIR, image_id)
                
                with open(file_path, "wb") as f:
                    f.write(response.content)
                
                saved_image_ids.append(image_id)
                logger.info(f"Successfully downloaded image {i}/{len(image_urls)}: {url} -> {image_id}")
                
            except httpx.HTTPStatusError as e:
                logger.error(f"HTTP error downloading image {i}/{len(image_urls)} from {url}: {e}")
            except httpx.RequestError as e:
                logger.error(f"Request error downloading image {i}/{len(image_urls)} from {url}: {e}")
            except OSError as e:
                logger.error(f"File system error saving image {i}/{len(image_urls)} from {url}: {e}")
            except Exception as e:
                logger.error(f"Unexpected error downloading image {i}/{len(image_urls)} from {url}: {e}")
    
    logger.info(f"Image download completed: {len(saved_image_ids)}/{len(image_urls)} successful")
    return saved_image_ids
