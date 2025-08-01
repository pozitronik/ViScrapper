import asyncio
import os
import math
from typing import List, Tuple, Dict, Any, Optional
from PIL import Image, ImageOps
from io import BytesIO
from utils.logger import get_logger
from exceptions.base import ImageProcessingException

logger = get_logger(__name__)


class ImageCombinationService:
    """Service for combining multiple images into a single optimized layout."""
    
    def __init__(self, spacing: int = 10, max_width: int = 1920, max_height: int = 1080):
        """
        Initialize the image combination service.
        
        Args:
            spacing: Spacing between images in pixels
            max_width: Maximum width of the combined image
            max_height: Maximum height of the combined image
        """
        self.spacing = spacing
        self.max_width = max_width
        self.max_height = max_height
    
    async def combine_images(
        self,
        image_paths: List[str],
        settings: Optional[Dict[str, Any]] = None
    ) -> List[bytes]:
        """
        Combine multiple images into optimized layouts. For 5+ images, creates multiple combined images.
        
        Args:
            image_paths: List of paths to image files
            settings: Optional settings dict with spacing, max_width, max_height
            
        Returns:
            List of combined images as bytes (JPEG format). Single item for ≤4 images, multiple for 5+ images.
            
        Raises:
            ImageProcessingException: If image combination fails
        """
        if not image_paths:
            raise ImageProcessingException(
                message="No images provided for combination",
                details={"image_count": 0}
            )
        
        # Update settings if provided
        if settings:
            self.spacing = settings.get("spacing", self.spacing)
            self.max_width = settings.get("max_width", self.max_width)
            self.max_height = settings.get("max_height", self.max_height)
        
        logger.info(f"Starting image combination for {len(image_paths)} images")
        
        try:
            # Load all images
            images = await self._load_images(image_paths)
            
            if not images:
                raise ImageProcessingException(
                    message="No valid images could be loaded",
                    details={"provided_paths": len(image_paths)}
                )
            
            # For 5+ images, split into groups of 4
            if len(images) > 4:
                return await self._combine_multiple_groups(images)
            else:
                # Single group processing
                grid_layout = self._calculate_optimal_grid(images)
                combined_image = self._create_combined_image(images, grid_layout)
                
                # Convert to bytes
                output = BytesIO()
                combined_image.save(output, format='JPEG', quality=95)
                image_bytes = output.getvalue()
                
                logger.info(f"Successfully combined {len(images)} images into {combined_image.size[0]}x{combined_image.size[1]} image ({len(image_bytes)} bytes)")
                
                return [image_bytes]
            
        except Exception as e:
            logger.error(f"Failed to combine images: {e}")
            raise ImageProcessingException(
                message="Failed to combine images",
                details={
                    "error": str(e),
                    "image_count": len(image_paths),
                    "settings": settings
                },
                original_exception=e
            )
    
    async def _combine_multiple_groups(self, images: List[Image.Image]) -> List[bytes]:
        """Combine 5+ images by splitting into groups of 4."""
        combined_images = []
        
        # Process images in groups of 4
        for i in range(0, len(images), 4):
            group = images[i:i+4]
            logger.info(f"Processing image group {i//4 + 1}: {len(group)} images")
            
            # Calculate layout for this group
            grid_layout = self._calculate_optimal_grid(group)
            combined_image = self._create_combined_image(group, grid_layout)
            
            # Convert to bytes
            output = BytesIO()
            combined_image.save(output, format='JPEG', quality=95)
            image_bytes = output.getvalue()
            
            combined_images.append(image_bytes)
            logger.info(f"Group {i//4 + 1} combined: {combined_image.size[0]}x{combined_image.size[1]} ({len(image_bytes)} bytes)")
        
        logger.info(f"Successfully created {len(combined_images)} combined images from {len(images)} original images")
        return combined_images
    
    async def _load_images(self, image_paths: List[str]) -> List[Image.Image]:
        """Load and validate images from file paths."""
        images = []
        
        for i, path in enumerate(image_paths):
            try:
                if not os.path.exists(path):
                    logger.warning(f"Image file not found: {path}")
                    continue
                
                with Image.open(path) as img:
                    # Convert to RGB if necessary
                    if img.mode != 'RGB':
                        img = img.convert('RGB')
                    
                    # Create a copy to ensure we can close the original
                    img_copy = img.copy()
                    images.append(img_copy)
                    
                logger.debug(f"Loaded image {i+1}/{len(image_paths)}: {path} ({img_copy.size[0]}x{img_copy.size[1]})")
                
            except Exception as e:
                logger.warning(f"Failed to load image {path}: {e}")
                continue
        
        return images
    
    def _calculate_optimal_grid(self, images: List[Image.Image]) -> Dict[str, Any]:
        """
        Calculate the optimal layout for images based on specific rules:
        1 image: show as is
        2 images: stack on bigger side  
        3 images: main image + 2 smaller (50%) on bigger side
        4 images: 2x2 grid
        5+ images: split into groups and process separately
        """
        image_count = len(images)
        
        if image_count == 1:
            return self._single_image_layout(images[0])
        elif image_count == 2:
            return self._two_images_layout(images)
        elif image_count == 3:
            return self._three_images_layout(images)
        elif image_count == 4:
            return self._four_images_layout(images)
        else:
            return self._multiple_images_layout(images)
    
    def _single_image_layout(self, image: Image.Image) -> Dict[str, Any]:
        """Layout for a single image."""
        width, height = image.size
        
        # Scale to fit within max dimensions while preserving aspect ratio
        scale_factor = min(self.max_width / width, self.max_height / height, 1.0)
        
        new_width = int(width * scale_factor)
        new_height = int(height * scale_factor)
        
        return {
            "grid_cols": 1,
            "grid_rows": 1,
            "canvas_width": new_width,
            "canvas_height": new_height,
            "positions": [
                {
                    "image_index": 0,
                    "x": 0,
                    "y": 0,
                    "width": new_width,
                    "height": new_height
                }
            ]
        }
    
    def _two_images_layout(self, images: List[Image.Image]) -> Dict[str, Any]:
        """
        Layout for two images - stack them on the bigger side.
        If images are more vertical (height > width), stack horizontally.
        If images are more horizontal (width > height), stack vertically.
        """
        img1, img2 = images
        
        # Determine the average aspect ratio
        avg_width = (img1.size[0] + img2.size[0]) / 2
        avg_height = (img1.size[1] + img2.size[1]) / 2
        
        # If images are taller than wide (vertical), place side by side
        # If images are wider than tall (horizontal), stack vertically
        if avg_height > avg_width:
            # Vertical images - place side by side
            return self._calculate_horizontal_layout([img1, img2])
        else:
            # Horizontal images - stack vertically  
            return self._calculate_vertical_layout([img1, img2])
    
    def _three_images_layout(self, images: List[Image.Image]) -> Dict[str, Any]:
        """
        Layout for three images: main image + 2 smaller (50%) on bigger side.
        For vertical main: [1][2] / [1][3] 
        For horizontal main: [1111] / [2][3]
        """
        main_img = images[0]
        img2, img3 = images[1], images[2]
        
        main_width, main_height = main_img.size
        
        # Determine if main image is more vertical or horizontal
        if main_height > main_width:
            # Vertical main image - place smaller images to the right
            return self._three_images_vertical_main(images)
        else:
            # Horizontal main image - place smaller images below
            return self._three_images_horizontal_main(images)
    
    def _four_images_layout(self, images: List[Image.Image]) -> Dict[str, Any]:
        """Layout for four images in a 2x2 grid."""
        return self._calculate_2x2_grid(images)
    
    def _multiple_images_layout(self, images: List[Image.Image]) -> Dict[str, Any]:
        """Layout for 5+ images - this shouldn't be called anymore as we handle grouping at service level."""
        # Fallback - just take first 4 images
        first_four = images[:4]
        return self._calculate_2x2_grid(first_four)
    
    def _three_images_vertical_main(self, images: List[Image.Image]) -> Dict[str, Any]:
        """
        Layout for vertical main image with 2 smaller images to the right:
        [1][2]
        [1][3]
        """
        main_img = images[0]
        img2, img3 = images[1], images[2]
        
        # Calculate scaling - smaller images are 50% of main image height
        main_width, main_height = main_img.size
        small_height = main_height // 2
        
        # Scale smaller images to fit 50% height while preserving aspect ratio
        img2_scale = small_height / img2.size[1]
        img3_scale = small_height / img3.size[1]
        
        img2_width = int(img2.size[0] * img2_scale)
        img3_width = int(img3.size[0] * img3_scale)
        
        # Use the wider of the two smaller images for layout
        small_section_width = max(img2_width, img3_width)
        
        # Total canvas dimensions
        total_width = main_width + self.spacing + small_section_width
        total_height = main_height
        
        # Scale everything to fit within max dimensions
        scale_factor = min(self.max_width / total_width, self.max_height / total_height, 1.0)
        
        # Apply scaling
        final_main_width = int(main_width * scale_factor)
        final_main_height = int(main_height * scale_factor)
        
        final_img2_width = int(img2_width * scale_factor)
        final_img2_height = int(small_height * scale_factor)
        
        final_img3_width = int(img3_width * scale_factor)
        final_img3_height = int(small_height * scale_factor)
        
        final_spacing = int(self.spacing * scale_factor)
        
        positions = [
            {
                "image_index": 0,
                "x": 0,
                "y": 0,
                "width": final_main_width,
                "height": final_main_height
            },
            {
                "image_index": 1,
                "x": final_main_width + final_spacing,
                "y": 0,
                "width": final_img2_width,
                "height": final_img2_height
            },
            {
                "image_index": 2,
                "x": final_main_width + final_spacing,
                "y": final_img2_height + final_spacing,
                "width": final_img3_width,
                "height": final_img3_height
            }
        ]
        
        return {
            "grid_cols": 2,
            "grid_rows": 2,
            "canvas_width": final_main_width + final_spacing + int(small_section_width * scale_factor),
            "canvas_height": final_main_height,
            "positions": positions
        }
    
    def _three_images_horizontal_main(self, images: List[Image.Image]) -> Dict[str, Any]:
        """
        Layout for horizontal main image with 2 smaller images below:
        [1111]
        [2][3]
        """
        main_img = images[0]
        img2, img3 = images[1], images[2]
        
        # Calculate scaling - smaller images are 50% of main image width each
        main_width, main_height = main_img.size
        small_width = main_width // 2
        
        # Scale smaller images to fit 50% width while preserving aspect ratio
        img2_scale = small_width / img2.size[0]
        img3_scale = small_width / img3.size[0]
        
        img2_height = int(img2.size[1] * img2_scale)
        img3_height = int(img3.size[1] * img3_scale)
        
        # Use the taller of the two smaller images for layout
        small_section_height = max(img2_height, img3_height)
        
        # Total canvas dimensions
        total_width = main_width
        total_height = main_height + self.spacing + small_section_height
        
        # Scale everything to fit within max dimensions
        scale_factor = min(self.max_width / total_width, self.max_height / total_height, 1.0)
        
        # Apply scaling
        final_main_width = int(main_width * scale_factor)
        final_main_height = int(main_height * scale_factor)
        
        final_img2_width = int(small_width * scale_factor)
        final_img2_height = int(img2_height * scale_factor)
        
        final_img3_width = int(small_width * scale_factor)
        final_img3_height = int(img3_height * scale_factor)
        
        final_spacing = int(self.spacing * scale_factor)
        
        positions = [
            {
                "image_index": 0,
                "x": 0,
                "y": 0,
                "width": final_main_width,
                "height": final_main_height
            },
            {
                "image_index": 1,
                "x": 0,
                "y": final_main_height + final_spacing,
                "width": final_img2_width,
                "height": final_img2_height
            },
            {
                "image_index": 2,
                "x": final_img2_width + final_spacing,
                "y": final_main_height + final_spacing,
                "width": final_img3_width,
                "height": final_img3_height
            }
        ]
        
        return {
            "grid_cols": 2,
            "grid_rows": 2,
            "canvas_width": final_main_width,
            "canvas_height": final_main_height + final_spacing + int(small_section_height * scale_factor),
            "positions": positions
        }
    
    def _calculate_2x2_grid(self, images: List[Image.Image]) -> Dict[str, Any]:
        """Calculate a simple 2x2 grid layout for up to 4 images with minimal gaps."""
        # Calculate optimal dimensions for each scaled image
        scaled_images = []
        for img in images[:4]:
            # Calculate max dimensions that fit in half the canvas
            max_img_width = (self.max_width - self.spacing) / 2
            max_img_height = (self.max_height - self.spacing) / 2
            
            # Scale image to fit while preserving aspect ratio
            scale = min(max_img_width / img.size[0], max_img_height / img.size[1], 1.0)
            scaled_width = int(img.size[0] * scale)
            scaled_height = int(img.size[1] * scale)
            
            scaled_images.append({
                "original": img,
                "width": scaled_width,
                "height": scaled_height,
                "scale": scale
            })
        
        # Find actual canvas size based on largest scaled images in each dimension
        max_top_width = max(scaled_images[0]["width"], scaled_images[1]["width"] if len(scaled_images) > 1 else 0)
        max_bottom_width = max(scaled_images[2]["width"] if len(scaled_images) > 2 else 0, 
                              scaled_images[3]["width"] if len(scaled_images) > 3 else 0)
        
        max_left_height = max(scaled_images[0]["height"], scaled_images[2]["height"] if len(scaled_images) > 2 else 0)
        max_right_height = max(scaled_images[1]["height"] if len(scaled_images) > 1 else 0,
                              scaled_images[3]["height"] if len(scaled_images) > 3 else 0)
        
        # Canvas dimensions based on actual content, not fixed grid
        canvas_width = max(max_top_width, max_bottom_width) * 2 + self.spacing
        canvas_height = max(max_left_height, max_right_height) * 2 + self.spacing
        
        # If canvas is too big, scale everything down
        if canvas_width > self.max_width or canvas_height > self.max_height:
            scale_factor = min(self.max_width / canvas_width, self.max_height / canvas_height)
            canvas_width = int(canvas_width * scale_factor)
            canvas_height = int(canvas_height * scale_factor)
            
            # Apply additional scaling to all images
            for scaled_img in scaled_images:
                scaled_img["width"] = int(scaled_img["width"] * scale_factor)
                scaled_img["height"] = int(scaled_img["height"] * scale_factor)
        
        # Calculate positions for 2x2 grid
        positions = []
        grid_positions = [(0, 0), (1, 0), (0, 1), (1, 1)]  # (col, row)
        
        for i, scaled_img in enumerate(scaled_images):
            if i >= 4:
                break
                
            col, row = grid_positions[i]
            
            # Calculate base position for this grid cell
            cell_width = (canvas_width - self.spacing) // 2
            cell_height = (canvas_height - self.spacing) // 2
            
            base_x = col * (cell_width + self.spacing)
            base_y = row * (cell_height + self.spacing)
            
            # Center image within its cell
            x = base_x + (cell_width - scaled_img["width"]) // 2
            y = base_y + (cell_height - scaled_img["height"]) // 2
            
            positions.append({
                "image_index": i,
                "x": x,
                "y": y,
                "width": scaled_img["width"],
                "height": scaled_img["height"]
            })
        
        return {
            "grid_cols": 2,
            "grid_rows": 2,
            "canvas_width": canvas_width,
            "canvas_height": canvas_height,
            "positions": positions
        }
    
    def _calculate_horizontal_layout(self, images: List[Image.Image]) -> Dict[str, Any]:
        """Calculate horizontal (side-by-side) layout."""
        total_width = sum(img.size[0] for img in images) + self.spacing * (len(images) - 1)
        max_height = max(img.size[1] for img in images)
        
        # Scale to fit within constraints
        scale_factor = min(self.max_width / total_width, self.max_height / max_height, 1.0)
        
        positions = []
        current_x = 0
        
        for i, img in enumerate(images):
            scaled_width = int(img.size[0] * scale_factor)
            scaled_height = int(img.size[1] * scale_factor)
            
            positions.append({
                "image_index": i,
                "x": current_x,
                "y": int((max_height * scale_factor - scaled_height) / 2),  # Center vertically
                "width": scaled_width,
                "height": scaled_height
            })
            
            current_x += scaled_width + int(self.spacing * scale_factor)
        
        return {
            "grid_cols": len(images),
            "grid_rows": 1,
            "canvas_width": int(total_width * scale_factor),
            "canvas_height": int(max_height * scale_factor),
            "positions": positions
        }
    
    def _calculate_vertical_layout(self, images: List[Image.Image]) -> Dict[str, Any]:
        """Calculate vertical (stacked) layout."""
        max_width = max(img.size[0] for img in images)
        total_height = sum(img.size[1] for img in images) + self.spacing * (len(images) - 1)
        
        # Scale to fit within constraints
        scale_factor = min(self.max_width / max_width, self.max_height / total_height, 1.0)
        
        positions = []
        current_y = 0
        
        for i, img in enumerate(images):
            scaled_width = int(img.size[0] * scale_factor)
            scaled_height = int(img.size[1] * scale_factor)
            
            positions.append({
                "image_index": i,
                "x": int((max_width * scale_factor - scaled_width) / 2),  # Center horizontally
                "y": current_y,
                "width": scaled_width,
                "height": scaled_height
            })
            
            current_y += scaled_height + int(self.spacing * scale_factor)
        
        return {
            "grid_cols": 1,
            "grid_rows": len(images),
            "canvas_width": int(max_width * scale_factor),
            "canvas_height": int(total_height * scale_factor),
            "positions": positions
        }
    
    
    def _create_combined_image(self, images: List[Image.Image], layout: Dict[str, Any]) -> Image.Image:
        """Create the final combined image based on layout."""
        # Create blank canvas
        combined = Image.new('RGB', (layout["canvas_width"], layout["canvas_height"]), 'white')
        
        # Place each image
        for pos in layout["positions"]:
            img_index = pos["image_index"]
            img = images[img_index]
            
            # Resize image to fit position
            resized_img = img.resize((pos["width"], pos["height"]), Image.Resampling.LANCZOS)
            
            # Paste image at position
            combined.paste(resized_img, (pos["x"], pos["y"]))
        
        return combined


async def combine_product_images(
    image_paths: List[str],
    max_width: int = 1920,
    max_height: int = 1080,
    spacing: int = 10
) -> List[bytes]:
    """
    Convenience function to combine product images.
    
    Args:
        image_paths: List of paths to image files
        max_width: Maximum width of combined image
        max_height: Maximum height of combined image
        spacing: Spacing between images in pixels
        
    Returns:
        List of combined images as bytes (JPEG format). Single item for ≤4 images, multiple items for 5+ images.
    """
    service = ImageCombinationService(spacing=spacing, max_width=max_width, max_height=max_height)
    return await service.combine_images(image_paths)