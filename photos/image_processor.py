"""
Enhanced image processing module with WebP support, responsive images, and optimization.
"""
import io
import logging
import hashlib
from typing import Optional, Tuple, List, Dict, Any
from PIL import Image, ImageOps, ExifTags
from django.core.files.base import ContentFile
from django.core.files.uploadedfile import InMemoryUploadedFile
from django.conf import settings

logger = logging.getLogger(__name__)

# Image processing settings
IMAGE_FORMATS = {
    'webp': {'quality': 85, 'method': 6, 'lossless': False},
    'jpeg': {'quality': 85, 'optimize': True, 'progressive': True},
    'png': {'compress_level': 9, 'optimize': True}
}

# Responsive image sizes
RESPONSIVE_SIZES = {
    'thumbnail': (400, 400),
    'small': (640, 480),
    'medium': (1024, 768),
    'large': (1920, 1080),
    'xlarge': (2560, 1440),
}

# Maximum file sizes (in bytes)
MAX_SIZES = {
    'thumbnail': 100 * 1024,  # 100KB
    'small': 200 * 1024,      # 200KB
    'medium': 500 * 1024,     # 500KB
    'large': 1024 * 1024,     # 1MB
    'xlarge': 2048 * 1024,    # 2MB
}


class ImageProcessor:
    """
    Advanced image processor with WebP support and responsive image generation.
    """
    
    def __init__(self, image_file):
        """
        Initialize the image processor.
        
        Args:
            image_file: Django ImageField or file-like object
        """
        self.original_file = image_file
        self.image = None
        self.original_format = None
        self.exif_data = None
        
    def load_image(self) -> Image.Image:
        """
        Load and prepare the image for processing.
        
        Returns:
            PIL Image object
        """
        if self.image is None:
            # Open the image
            self.image = Image.open(self.original_file)
            self.original_format = self.image.format.lower() if self.image.format else 'jpeg'
            
            # Convert RGBA to RGB for JPEG
            if self.image.mode == 'RGBA' and self.original_format in ['jpeg', 'jpg']:
                background = Image.new('RGB', self.image.size, (255, 255, 255))
                background.paste(self.image, mask=self.image.split()[3])
                self.image = background
            elif self.image.mode not in ['RGB', 'RGBA']:
                self.image = self.image.convert('RGB')
            
            # Extract and apply EXIF orientation
            self.exif_data = self._get_exif_data()
            self.image = self._apply_exif_orientation(self.image)
            
        return self.image
    
    def _get_exif_data(self) -> Optional[dict]:
        """
        Extract EXIF data from the image.
        
        Returns:
            Dictionary of EXIF data or None
        """
        try:
            exif = self.image._getexif()
            if exif:
                return {
                    ExifTags.TAGS[k]: v
                    for k, v in exif.items()
                    if k in ExifTags.TAGS
                }
        except (AttributeError, KeyError, IndexError):
            pass
        return None
    
    def _apply_exif_orientation(self, image: Image.Image) -> Image.Image:
        """
        Apply EXIF orientation to the image.
        
        Args:
            image: PIL Image object
            
        Returns:
            Properly oriented image
        """
        if not self.exif_data:
            return image
            
        orientation = self.exif_data.get('Orientation')
        if orientation:
            if orientation == 3:
                image = image.rotate(180, expand=True)
            elif orientation == 6:
                image = image.rotate(270, expand=True)
            elif orientation == 8:
                image = image.rotate(90, expand=True)
                
        return image
    
    def generate_thumbnail(self, size: Tuple[int, int] = None, 
                          format: str = 'jpeg') -> ContentFile:
        """
        Generate an optimized thumbnail.
        
        Args:
            size: Thumbnail size (width, height)
            format: Output format (jpeg, webp, png)
            
        Returns:
            ContentFile with thumbnail data
        """
        size = size or RESPONSIVE_SIZES['thumbnail']
        image = self.load_image().copy()
        
        # Use LANCZOS resampling for better quality
        image.thumbnail(size, Image.Resampling.LANCZOS)
        
        # Apply smart cropping for better composition
        image = ImageOps.fit(image, size, Image.Resampling.LANCZOS, centering=(0.5, 0.5))
        
        return self._save_image(image, format, 'thumbnail')
    
    def generate_responsive_images(self, formats: List[str] = None) -> Dict[str, Dict[str, ContentFile]]:
        """
        Generate multiple responsive image sizes in different formats.
        
        Args:
            formats: List of output formats (default: ['jpeg', 'webp'])
            
        Returns:
            Dictionary of size -> format -> ContentFile
        """
        formats = formats or ['jpeg', 'webp']
        responsive_images = {}
        
        image = self.load_image()
        
        for size_name, dimensions in RESPONSIVE_SIZES.items():
            responsive_images[size_name] = {}
            
            # Skip sizes larger than original
            if dimensions[0] > image.width or dimensions[1] > image.height:
                continue
            
            for format in formats:
                try:
                    # Create resized image
                    resized = image.copy()
                    resized.thumbnail(dimensions, Image.Resampling.LANCZOS)
                    
                    # Save in specified format
                    content_file = self._save_image(resized, format, size_name)
                    responsive_images[size_name][format] = content_file
                    
                    logger.debug(f"Generated {size_name} image in {format} format")
                    
                except Exception as e:
                    logger.error(f"Error generating {size_name} in {format}: {str(e)}")
        
        return responsive_images
    
    def generate_webp(self, size: Optional[Tuple[int, int]] = None, 
                     quality: int = 85) -> ContentFile:
        """
        Generate WebP version of the image.
        
        Args:
            size: Optional size to resize to
            quality: WebP quality (1-100)
            
        Returns:
            ContentFile with WebP data
        """
        image = self.load_image().copy()
        
        if size:
            image.thumbnail(size, Image.Resampling.LANCZOS)
        
        output = io.BytesIO()
        image.save(
            output,
            format='WEBP',
            quality=quality,
            method=6,  # Slowest but best compression
            lossless=False
        )
        
        return ContentFile(output.getvalue())
    
    def optimize_image(self, target_size: Optional[int] = None, 
                      format: Optional[str] = None) -> ContentFile:
        """
        Optimize image for web delivery.
        
        Args:
            target_size: Target file size in bytes
            format: Output format
            
        Returns:
            Optimized image as ContentFile
        """
        image = self.load_image()
        format = format or self.original_format or 'jpeg'
        
        # Start with high quality
        quality = 95
        output = None
        
        # Binary search for optimal quality
        min_quality = 60
        max_quality = 95
        
        while min_quality <= max_quality:
            current_quality = (min_quality + max_quality) // 2
            output = io.BytesIO()
            
            save_kwargs = self._get_save_kwargs(format, current_quality)
            image.save(output, format=format.upper(), **save_kwargs)
            
            size = output.tell()
            
            if target_size and size > target_size:
                max_quality = current_quality - 1
            else:
                quality = current_quality
                if target_size and size < target_size * 0.9:
                    min_quality = current_quality + 1
                else:
                    break
        
        output.seek(0)
        logger.info(f"Optimized image to {output.tell()} bytes at quality {quality}")
        
        return ContentFile(output.getvalue())
    
    def _save_image(self, image: Image.Image, format: str, 
                   size_name: str) -> ContentFile:
        """
        Save image with optimal settings for format.
        
        Args:
            image: PIL Image object
            format: Output format
            size_name: Size identifier for optimization
            
        Returns:
            ContentFile with image data
        """
        output = io.BytesIO()
        
        # Get format-specific save parameters
        save_kwargs = self._get_save_kwargs(format)
        
        # Adjust quality based on size
        if size_name == 'thumbnail':
            save_kwargs['quality'] = min(save_kwargs.get('quality', 85), 80)
        elif size_name in ['xlarge']:
            save_kwargs['quality'] = max(save_kwargs.get('quality', 85), 90)
        
        # Save the image
        image.save(output, format=format.upper(), **save_kwargs)
        
        # Check file size and re-compress if needed
        output_size = output.tell()
        max_size = MAX_SIZES.get(size_name)
        
        if max_size and output_size > max_size:
            # Reduce quality to meet size requirements
            output = self._reduce_to_size(image, format, max_size)
        
        output.seek(0)
        return ContentFile(output.getvalue())
    
    def _get_save_kwargs(self, format: str, quality: Optional[int] = None) -> dict:
        """
        Get save parameters for specific format.
        
        Args:
            format: Image format
            quality: Optional quality override
            
        Returns:
            Dictionary of save parameters
        """
        format = format.lower()
        kwargs = IMAGE_FORMATS.get(format, {}).copy()
        
        if quality is not None and 'quality' in kwargs:
            kwargs['quality'] = quality
        
        return kwargs
    
    def _reduce_to_size(self, image: Image.Image, format: str, 
                       max_size: int) -> io.BytesIO:
        """
        Reduce image file size to meet maximum size requirement.
        
        Args:
            image: PIL Image object
            format: Output format
            max_size: Maximum file size in bytes
            
        Returns:
            BytesIO with compressed image
        """
        quality = 85
        output = io.BytesIO()
        
        while quality >= 60:
            output = io.BytesIO()
            save_kwargs = self._get_save_kwargs(format, quality)
            image.save(output, format=format.upper(), **save_kwargs)
            
            if output.tell() <= max_size:
                break
            
            quality -= 5
        
        return output
    
    def generate_srcset(self, formats: List[str] = None) -> Dict[str, List[str]]:
        """
        Generate srcset attribute values for responsive images.
        
        Args:
            formats: List of formats to generate
            
        Returns:
            Dictionary of format -> list of srcset values
        """
        formats = formats or ['jpeg', 'webp']
        srcsets = {}
        
        responsive_images = self.generate_responsive_images(formats)
        
        for format in formats:
            srcset_values = []
            
            for size_name, size_images in responsive_images.items():
                if format in size_images:
                    width = RESPONSIVE_SIZES[size_name][0]
                    # In a real implementation, you'd upload these and get URLs
                    url = f"/media/responsive/{size_name}.{format}"
                    srcset_values.append(f"{url} {width}w")
            
            srcsets[format] = srcset_values
        
        return srcsets
    
    def get_dominant_color(self) -> str:
        """
        Get the dominant color of the image for placeholder backgrounds.
        
        Returns:
            Hex color string
        """
        image = self.load_image()
        
        # Resize for faster processing
        small_image = image.copy()
        small_image.thumbnail((50, 50))
        
        # Get most common color
        colors = small_image.getcolors(maxcolors=256)
        if colors:
            most_common = max(colors, key=lambda x: x[0])
            rgb = most_common[1][:3] if len(most_common[1]) >= 3 else (128, 128, 128)
            return '#{:02x}{:02x}{:02x}'.format(*rgb)
        
        return '#808080'  # Default gray
    
    def generate_blur_placeholder(self, size: Tuple[int, int] = (20, 20)) -> str:
        """
        Generate a base64-encoded blur placeholder for lazy loading.
        
        Args:
            size: Size of the placeholder image
            
        Returns:
            Base64-encoded data URL
        """
        import base64
        
        image = self.load_image().copy()
        image.thumbnail(size, Image.Resampling.LANCZOS)
        
        # Apply blur
        from PIL import ImageFilter
        image = image.filter(ImageFilter.GaussianBlur(radius=2))
        
        # Convert to base64
        output = io.BytesIO()
        image.save(output, format='JPEG', quality=40)
        output.seek(0)
        
        base64_data = base64.b64encode(output.getvalue()).decode('utf-8')
        return f"data:image/jpeg;base64,{base64_data}"


def process_uploaded_image(image_file, generate_all_sizes: bool = False) -> Dict[str, Any]:
    """
    Process an uploaded image with all optimizations.
    
    Args:
        image_file: Uploaded image file
        generate_all_sizes: Whether to generate all responsive sizes
        
    Returns:
        Dictionary with processed image data
    """
    processor = ImageProcessor(image_file)
    result = {
        'original': image_file,
        'thumbnail': processor.generate_thumbnail(),
        'webp_thumbnail': processor.generate_webp(RESPONSIVE_SIZES['thumbnail']),
        'dominant_color': processor.get_dominant_color(),
        'blur_placeholder': processor.generate_blur_placeholder(),
    }
    
    if generate_all_sizes:
        result['responsive'] = processor.generate_responsive_images()
        result['srcsets'] = processor.generate_srcset()
    
    return result