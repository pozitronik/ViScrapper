import httpx
import os
import uuid
from typing import List

IMAGE_DIR = os.getenv("IMAGE_DIR", "./images")

async def download_images(image_urls: List[str]) -> List[str]:
    if not os.path.exists(IMAGE_DIR):
        os.makedirs(IMAGE_DIR)

    saved_image_ids = []
    async with httpx.AsyncClient() as client:
        for url in image_urls:
            try:
                response = await client.get(str(url))
                response.raise_for_status()
                image_id = f"{uuid.uuid4()}.jpg"
                with open(os.path.join(IMAGE_DIR, image_id), "wb") as f:
                    f.write(response.content)
                saved_image_ids.append(image_id)
            except httpx.HTTPStatusError as e:
                print(f"Error downloading {url}: {e}")
            except Exception as e:
                print(f"An unexpected error occurred: {e}")
    return saved_image_ids
