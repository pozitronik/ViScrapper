import pytest
import os

from services import image_downloader


@pytest.mark.asyncio
async def test_download_images(httpx_mock):
    IMAGE_URL = "http://example.com/image.jpg"
    httpx_mock.add_response(
        url=IMAGE_URL, 
        content=b"fake image data",
        headers={"content-type": "image/jpeg"}
    )

    saved_metadata = await image_downloader.download_images([IMAGE_URL])
    assert len(saved_metadata) == 1
    
    # Check metadata structure
    metadata = saved_metadata[0]
    assert metadata["success"] is True
    assert metadata["url"] == IMAGE_URL
    assert "image_id" in metadata
    assert "file_hash" in metadata
    
    # Check file was actually saved
    image_path = os.path.join(image_downloader.IMAGE_DIR, metadata["image_id"])
    assert os.path.exists(image_path)
    with open(image_path, "rb") as f:
        assert f.read() == b"fake image data"
    os.remove(image_path)
