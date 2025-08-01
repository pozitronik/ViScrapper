import asyncio
import os
from typing import Dict, Any, Optional, Tuple
from PIL import Image, ImageOps
from io import BytesIO
from utils.logger import get_logger
from exceptions.base import ImageProcessingException

logger = get_logger(__name__)


class ImageOptimizationService:
    """Service for optimizing images with compression and resizing."""
    
    def __init__(
        self,
        max_file_size_kb: int = 500,
        max_width: int = 1920,
        max_height: int = 1080,
        compression_quality: int = 80
    ):
        """
        Initialize the image optimization service.
        
        Args:
            max_file_size_kb: Maximum file size in KB
            max_width: Maximum image width in pixels
            max_height: Maximum image height in pixels
            compression_quality: JPEG compression quality percentage (10-100)
        """
        self.max_file_size_kb = max_file_size_kb
        self.max_width = max_width
        self.max_height = max_height
        self.compression_quality = compression_quality
        self.max_file_size_bytes = max_file_size_kb * 1024
    
    async def optimize_image(
        self,
        image_data: bytes,
        settings: Optional[Dict[str, Any]] = None
    ) -> bytes:
        """
        Optimize image with compression and resizing.
        
        Args:
            image_data: Image data as bytes
            settings: Optional settings dict to override defaults
            
        Returns:
            Optimized image as bytes (JPEG format)
            
        Raises:
            ImageProcessingException: If image optimization fails
        """
        if not image_data:
            raise ImageProcessingException(
                message="No image data provided for optimization",
                details={"data_size": 0}
            )
        
        # Update settings if provided
        if settings:
            self.max_file_size_kb = settings.get("max_file_size_kb", self.max_file_size_kb)
            self.max_width = settings.get("max_width", self.max_width)
            self.max_height = settings.get("max_height", self.max_height)
            self.compression_quality = settings.get("compression_quality", self.compression_quality)
            self.max_file_size_bytes = self.max_file_size_kb * 1024
        
        original_size = len(image_data)
        logger.info(f"Starting image optimization (original size: {original_size} bytes, target: {self.max_file_size_bytes} bytes)")
        
        try:
            # Load image
            with Image.open(BytesIO(image_data)) as img:
                # Convert to RGB if necessary
                if img.mode != 'RGB':
                    img = img.convert('RGB')
                
                # Create a copy to work with
                optimized_img = img.copy()
            
            original_dimensions = optimized_img.size
            logger.debug(f"Original image dimensions: {original_dimensions[0]}x{original_dimensions[1]}")
            
            # Step 1: Resize if dimensions exceed limits
            optimized_img = self._resize_to_limits(optimized_img)
            
            # Step 2: Try to achieve target file size with current quality
            optimized_data = self._compress_image(optimized_img, self.compression_quality)
            
            # Step 3: If still too large, reduce compression quality
            if len(optimized_data) > self.max_file_size_bytes:
                optimized_data = self._optimize_compression(optimized_img)
            
            # Step 4: If still too large, reduce dimensions further
            if len(optimized_data) > self.max_file_size_bytes:
                optimized_img, optimized_data = self._optimize_dimensions(optimized_img)
            
            final_size = len(optimized_data)
            final_dimensions = optimized_img.size
            compression_ratio = (1 - final_size / original_size) * 100 if original_size > 0 else 0
            
            logger.info(
                f"Image optimization completed: {original_size} -> {final_size} bytes "
                f"({compression_ratio:.1f}% reduction), {original_dimensions} -> {final_dimensions}"
            )
            
            return optimized_data
            
        except Exception as e:
            logger.error(f"Failed to optimize image: {e}")
            raise ImageProcessingException(
                message="Failed to optimize image",
                details={
                    "error": str(e),
                    "original_size": len(image_data),
                    "settings": settings
                },
                original_exception=e
            )
    
    async def optimize_image_file(
        self,
        input_path: str,
        output_path: Optional[str] = None,
        settings: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Optimize image file and save result.
        
        Args:
            input_path: Path to input image file
            output_path: Path for output file (defaults to input_path with _optimized suffix)
            settings: Optional settings dict to override defaults
            
        Returns:
            Path to optimized image file
            
        Raises:
            ImageProcessingException: If image optimization fails
        """
        if not os.path.exists(input_path):
            raise ImageProcessingException(
                message="Input image file not found",
                details={"input_path": input_path}
            )
        
        try:
            # Read input file
            with open(input_path, 'rb') as f:
                image_data = f.read()
            
            # Optimize image
            optimized_data = await self.optimize_image(image_data, settings)
            
            # Determine output path
            if not output_path:
                name, ext = os.path.splitext(input_path)
                output_path = f"{name}_optimized.jpg"
            
            # Save optimized image
            with open(output_path, 'wb') as f:
                f.write(optimized_data)
            
            logger.info(f"Optimized image saved to: {output_path}")
            return output_path
            
        except ImageProcessingException:
            raise
        except Exception as e:
            logger.error(f"Failed to optimize image file {input_path}: {e}")
            raise ImageProcessingException(
                message="Failed to optimize image file",
                details={
                    "input_path": input_path,
                    "output_path": output_path,
                    "error": str(e)
                },
                original_exception=e
            )
    
    def _resize_to_limits(self, img: Image.Image) -> Image.Image:
        """Resize image to fit within maximum dimensions while preserving aspect ratio."""
        width, height = img.size
        
        if width <= self.max_width and height <= self.max_height:
            return img
        
        # Calculate scale factor
        scale_factor = min(self.max_width / width, self.max_height / height)
        
        new_width = int(width * scale_factor)
        new_height = int(height * scale_factor)
        
        logger.debug(f"Resizing image from {width}x{height} to {new_width}x{new_height}")
        
        return img.resize((new_width, new_height), Image.Resampling.LANCZOS)
    
    def _compress_image(self, img: Image.Image, quality: int) -> bytes:
        """Compress image with specified quality."""
        output = BytesIO()
        img.save(output, format='JPEG', quality=quality, optimize=True)
        return output.getvalue()
    
    def _optimize_compression(self, img: Image.Image) -> bytes:
        """Optimize compression quality to meet file size target."""
        # Try different quality levels from current quality down to 10
        qualities = list(range(self.compression_quality, 9, -5))  # Step down by 5
        qualities.append(10)  # Ensure we try minimum quality
        
        best_data = None
        best_quality = self.compression_quality
        
        for quality in qualities:
            compressed_data = self._compress_image(img, quality)
            
            if len(compressed_data) <= self.max_file_size_bytes:
                logger.debug(f"Achieved target file size with quality {quality}")
                return compressed_data
            
            # Keep track of best result even if not within target
            if best_data is None or len(compressed_data) < len(best_data):
                best_data = compressed_data
                best_quality = quality
        
        logger.debug(f"Best compression achieved with quality {best_quality}")
        return best_data or self._compress_image(img, 10)
    
    def _optimize_dimensions(self, img: Image.Image) -> Tuple[Image.Image, bytes]:
        """Optimize image dimensions to meet file size target."""
        width, height = img.size
        
        # Try reducing dimensions in steps
        scale_factors = [0.9, 0.8, 0.7, 0.6, 0.5, 0.4, 0.3]
        
        for scale_factor in scale_factors:
            new_width = int(width * scale_factor)
            new_height = int(height * scale_factor)
            
            # Don't go below reasonable minimum size
            if new_width < 200 or new_height < 200:
                break
            
            resized_img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
            
            # Try with optimized compression
            compressed_data = self._optimize_compression_for_resized(resized_img)
            
            if len(compressed_data) <= self.max_file_size_bytes:
                logger.debug(f"Achieved target file size with dimensions {new_width}x{new_height}")
                return resized_img, compressed_data
        
        # If still too large, use smallest acceptable size with minimum quality
        final_scale = max(scale_factors)
        final_width = max(int(width * final_scale), 200)
        final_height = max(int(height * final_scale), 200)
        
        final_img = img.resize((final_width, final_height), Image.Resampling.LANCZOS)
        final_data = self._compress_image(final_img, 10)
        
        logger.warning(f"Could not achieve target file size, using minimum quality with {final_width}x{final_height}")
        return final_img, final_data
    
    def _optimize_compression_for_resized(self, img: Image.Image) -> bytes:
        """Optimize compression for a resized image."""
        # Start with current quality and work down
        qualities = list(range(self.compression_quality, 9, -10))  # Larger steps for resized images
        qualities.append(10)
        
        for quality in qualities:
            compressed_data = self._compress_image(img, quality)
            if len(compressed_data) <= self.max_file_size_bytes:
                return compressed_data
        
        # Return minimum quality if nothing else works
        return self._compress_image(img, 10)
    
    def get_optimization_info(self, original_data: bytes, optimized_data: bytes) -> Dict[str, Any]:
        """Get optimization statistics."""
        original_size = len(original_data)
        optimized_size = len(optimized_data)
        compression_ratio = (1 - optimized_size / original_size) * 100 if original_size > 0 else 0
        
        return {
            "original_size_bytes": original_size,
            "optimized_size_bytes": optimized_size,
            "compression_ratio_percent": round(compression_ratio, 1),
            "size_reduction_bytes": original_size - optimized_size,
            "target_size_bytes": self.max_file_size_bytes,
            "target_achieved": optimized_size <= self.max_file_size_bytes
        }


async def optimize_product_image(
    image_data: bytes,
    max_file_size_kb: int = 500,
    max_width: int = 1920,
    max_height: int = 1080,
    compression_quality: int = 80
) -> bytes:
    """
    Convenience function to optimize a product image.
    
    Args:
        image_data: Image data as bytes
        max_file_size_kb: Maximum file size in KB
        max_width: Maximum image width in pixels
        max_height: Maximum image height in pixels
        compression_quality: JPEG compression quality percentage (10-100)
        
    Returns:
        Optimized image as bytes (JPEG format)
    """
    service = ImageOptimizationService(
        max_file_size_kb=max_file_size_kb,
        max_width=max_width,
        max_height=max_height,
        compression_quality=compression_quality
    )
    return await service.optimize_image(image_data)