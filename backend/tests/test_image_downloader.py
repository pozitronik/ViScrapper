import pytest
import os

from backend.services import image_downloader


@pytest.mark.asyncio
async def test_download_images(httpx_mock):
    IMAGE_URL = "http://example.com/image.jpg"
    httpx_mock.add_response(url=IMAGE_URL, content=b"fake image data")

    saved_files = await image_downloader.download_images([IMAGE_URL])
    assert len(saved_files) == 1
    image_path = os.path.join(image_downloader.IMAGE_DIR, saved_files[0])
    assert os.path.exists(image_path)
    with open(image_path, "rb") as f:
        assert f.read() == b"fake image data"
    os.remove(image_path)
