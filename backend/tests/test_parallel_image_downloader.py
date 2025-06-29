"""
Tests for parallel image downloading functionality.
"""

import pytest
import asyncio
import time
import os
from unittest.mock import Mock, patch, AsyncMock
import httpx

from services.image_downloader import download_images, download_single_image, MAX_CONCURRENT_DOWNLOADS
from exceptions.base import ImageDownloadException, ExternalServiceException


class TestParallelImageDownloader:
    """Test parallel image downloading functionality."""

    @pytest.mark.asyncio
    async def test_parallel_download_multiple_images_success(self, httpx_mock):
        """Test successful parallel download of multiple images."""
        image_urls = [
            "http://example.com/image1.jpg",
            "http://example.com/image2.jpg", 
            "http://example.com/image3.jpg"
        ]
        
        # Mock responses for all images
        for url in image_urls:
            httpx_mock.add_response(
                url=url,
                content=f"fake image data for {url}".encode(),
                headers={"content-type": "image/jpeg"}
            )
        
        start_time = time.time()
        saved_metadata = await download_images(image_urls)
        end_time = time.time()
        
        # Verify results
        assert len(saved_metadata) == 3
        
        # Verify all files exist and contain correct content
        image_dir = os.getenv("IMAGE_DIR", "./images")
        for i, metadata in enumerate(saved_metadata):
            assert metadata["success"] is True
            assert metadata["url"] == image_urls[i]
            assert "image_id" in metadata
            assert "file_hash" in metadata
            
            file_path = os.path.join(image_dir, metadata["image_id"])
            assert os.path.exists(file_path)
            
            with open(file_path, "rb") as f:
                content = f.read()
                expected_content = f"fake image data for {image_urls[i]}".encode()
                assert content == expected_content
            
            # Clean up
            os.remove(file_path)
        
        # Parallel download should be faster than sequential
        # (This is a rough check - in practice the difference would be more significant)
        download_time = end_time - start_time
        assert download_time < 10  # Should complete quickly with mocked responses

    @pytest.mark.asyncio
    async def test_parallel_download_with_failures(self, httpx_mock):
        """Test parallel download where some images fail."""
        image_urls = [
            "http://example.com/image1.jpg",  # Success
            "http://example.com/image2.jpg",  # 404 error
            "http://example.com/image3.jpg",  # Success
            "http://example.com/image4.jpg",  # Invalid content type
        ]
        
        # Mock responses
        httpx_mock.add_response(
            url=image_urls[0],
            content=b"fake image data 1",
            headers={"content-type": "image/jpeg"}
        )
        httpx_mock.add_response(
            url=image_urls[1],
            status_code=404
        )
        httpx_mock.add_response(
            url=image_urls[2], 
            content=b"fake image data 3",
            headers={"content-type": "image/jpeg"}
        )
        httpx_mock.add_response(
            url=image_urls[3],
            content=b"not an image",
            headers={"content-type": "text/html"}
        )
        
        saved_metadata = await download_images(image_urls)
        
        # Should have 2 successful downloads (some failures expected)
        successful_downloads = [m for m in saved_metadata if m["success"]]
        assert len(successful_downloads) == 2
        
        # Clean up files
        for metadata in successful_downloads:
            file_path = os.path.join("./images", metadata["image_id"])
            if os.path.exists(file_path):
                os.remove(file_path)

    @pytest.mark.asyncio
    async def test_parallel_download_concurrency_limit(self):
        """Test that concurrency is properly limited."""
        # Create a custom mock that tracks concurrent requests
        concurrent_requests = 0
        max_concurrent = 0
        
        async def mock_get(url, **kwargs):
            nonlocal concurrent_requests, max_concurrent
            concurrent_requests += 1
            max_concurrent = max(max_concurrent, concurrent_requests)
            
            # Simulate some processing time
            await asyncio.sleep(0.1)
            
            concurrent_requests -= 1
            
            # Return mock response
            response = Mock()
            response.headers = {"content-type": "image/jpeg"}
            response.content = b"fake image data"
            response.raise_for_status = Mock()
            return response
        
        # Test with more URLs than the concurrency limit
        image_urls = [f"http://example.com/image{i}.jpg" for i in range(10)]
        
        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client = Mock()
            mock_client.get = mock_get
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client_class.return_value = mock_client
            
            saved_metadata = await download_images(image_urls)
            
            # Verify concurrency was limited
            assert max_concurrent <= MAX_CONCURRENT_DOWNLOADS
            successful_downloads = [m for m in saved_metadata if m["success"]]
            assert len(successful_downloads) == 10
            
            # Clean up files
            for metadata in successful_downloads:
                file_path = os.path.join("./images", metadata["image_id"])
                if os.path.exists(file_path):
                    os.remove(file_path)

    @pytest.mark.asyncio
    async def test_download_single_image_retry_logic(self):
        """Test retry logic for a single image download."""
        url = "http://example.com/image.jpg"
        
        # Mock client that fails twice then succeeds
        call_count = 0
        
        async def mock_get(url_param, **kwargs):
            nonlocal call_count
            call_count += 1
            
            if call_count <= 2:
                # First two calls fail with 503 (server error - should retry)
                response = Mock()
                response.status_code = 503
                error = httpx.HTTPStatusError("Service unavailable", request=Mock(), response=response)
                raise error
            else:
                # Third call succeeds
                response = Mock()
                response.headers = {"content-type": "image/jpeg"}
                response.content = b"fake image data"
                response.raise_for_status = Mock()
                return response
        
        semaphore = asyncio.Semaphore(1)
        
        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client = Mock()
            mock_client.get = mock_get
            mock_client_class.return_value = mock_client
            
            result = await download_single_image(mock_client, url, semaphore, 1, 1)
            
            # Should succeed after retries
            assert result["success"] is True
            assert call_count == 3  # Two failures + one success
            
            # Clean up
            if result.get("image_id"):
                file_path = os.path.join("./images", result["image_id"])
                if os.path.exists(file_path):
                    os.remove(file_path)

    @pytest.mark.asyncio
    async def test_download_single_image_no_retry_on_client_error(self):
        """Test that client errors (4xx) don't trigger retries."""
        url = "http://example.com/image.jpg"
        
        call_count = 0
        
        async def mock_get(url_param, **kwargs):
            nonlocal call_count
            call_count += 1
            
            # Always return 404 (client error - should not retry)
            response = Mock()
            response.status_code = 404
            error = httpx.HTTPStatusError("Not found", request=Mock(), response=response)
            raise error
        
        semaphore = asyncio.Semaphore(1)
        
        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client = Mock()
            mock_client.get = mock_get
            mock_client_class.return_value = mock_client
            
            result = await download_single_image(mock_client, url, semaphore, 1, 1)
            
            # Should fail without retries
            assert result["success"] is False
            assert result["error"] == "HTTP error"
            assert call_count == 1  # No retries for 4xx errors

    @pytest.mark.asyncio
    async def test_parallel_download_all_fail_exception(self, httpx_mock):
        """Test exception when all parallel downloads fail with multiple images."""
        image_urls = [
            "http://example.com/image1.jpg",
            "http://example.com/image2.jpg"
        ]
        
        # Mock all requests to fail
        for url in image_urls:
            httpx_mock.add_response(url=url, status_code=404)
        
        with pytest.raises(ImageDownloadException) as exc_info:
            await download_images(image_urls)
        
        assert "Failed to download any images" in str(exc_info.value)
        assert exc_info.value.error_code == "IMAGE_DOWNLOAD_ERROR"

    @pytest.mark.asyncio
    async def test_parallel_download_single_image_no_exception(self, httpx_mock):
        """Test that single image failure doesn't raise exception."""
        image_urls = ["http://example.com/image.jpg"]
        
        httpx_mock.add_response(url=image_urls[0], status_code=404)
        
        # Should return empty list, not raise exception
        result = await download_images(image_urls)
        assert result == []

    @pytest.mark.asyncio
    async def test_parallel_download_large_image_rejection(self, httpx_mock):
        """Test that oversized images are rejected in parallel download."""
        image_urls = [
            "http://example.com/small_image.jpg",
            "http://example.com/large_image.jpg"
        ]
        
        # Mock responses - one normal, one oversized
        httpx_mock.add_response(
            url=image_urls[0],
            content=b"small image data",
            headers={"content-type": "image/jpeg"}
        )
        httpx_mock.add_response(
            url=image_urls[1], 
            content=b"x" * (11 * 1024 * 1024),  # 11MB > 10MB limit
            headers={"content-type": "image/jpeg"}
        )
        
        saved_metadata = await download_images(image_urls)
        
        # Should only save the small image (large one should be rejected)
        successful_downloads = [m for m in saved_metadata if m["success"]]
        assert len(successful_downloads) == 1
        
        # Clean up
        for metadata in successful_downloads:
            file_path = os.path.join("./images", metadata["image_id"])
            if os.path.exists(file_path):
                os.remove(file_path)

    @pytest.mark.asyncio  
    async def test_parallel_download_directory_creation_error(self):
        """Test error handling when image directory creation fails."""
        image_urls = ["http://example.com/image.jpg"]
        
        with patch('os.path.exists', return_value=False), \
             patch('os.makedirs', side_effect=OSError("Permission denied")):
            
            with pytest.raises(ExternalServiceException) as exc_info:
                await download_images(image_urls)
            
            assert "Failed to create image directory" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_parallel_download_empty_list(self):
        """Test parallel download with empty URL list."""
        result = await download_images([])
        assert result == []

    @pytest.mark.asyncio
    async def test_parallel_download_performance_improvement(self, httpx_mock):
        """Test that parallel download is faster than sequential would be."""
        # Simulate multiple images
        image_urls = [f"http://example.com/image{i}.jpg" for i in range(5)]
        
        # Mock responses for all images
        for url in image_urls:
            httpx_mock.add_response(
                url=url,
                content=b"fake image data",
                headers={"content-type": "image/jpeg"}
            )
        
        start_time = time.time()
        saved_metadata = await download_images(image_urls)
        end_time = time.time()
        
        download_time = end_time - start_time
        
        # Verify all downloads succeeded
        successful_downloads = [m for m in saved_metadata if m["success"]]
        assert len(successful_downloads) == 5
        
        # Parallel download should complete quickly with mocked responses
        assert download_time < 2.0  # Should complete quickly
        
        # Clean up
        for metadata in successful_downloads:
            file_path = os.path.join("./images", metadata["image_id"])
            if os.path.exists(file_path):
                os.remove(file_path)