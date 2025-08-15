"""
Image processing utilities for optimizing images before uploading to S3.
"""
from PIL import Image
from io import BytesIO
from django.core.files.base import ContentFile
import os


class ImageOptimizer:
    """
    Handles image optimization and resizing for different use cases.
    """
    
    # Define size presets for different use cases
    SIZES = {
        'thumbnail': (150, 150),
        'small': (400, 400),
        'medium': (800, 800),
        'large': (1920, 1920),
        # 'full' will be the original image
    }
    
    # Quality settings for JPEG compression
    QUALITY_SETTINGS = {
        'thumbnail': 70,
        'small': 80,
        'medium': 85,
        'large': 90,
        'full': 100,  # No quality reduction for full size
    }
    
    @classmethod
    def optimize_image(cls, image_file, size_name='full', maintain_aspect_ratio=True):
        """
        Optimize an image file for a specific size.
        
        Args:
            image_file: Django ImageField file or file-like object
            size_name: One of 'thumbnail', 'small', 'medium', 'large', or 'full'
            maintain_aspect_ratio: If True, maintains aspect ratio when resizing
            
        Returns:
            ContentFile: Optimized image ready for saving (or original if 'full')
        """
        # For full size, return the original file without any processing
        if size_name == 'full':
            image_file.seek(0)
            return ContentFile(image_file.read())
        
        # Open the image for processing other sizes
        img = Image.open(image_file)
        
        # Convert RGBA to RGB if necessary (for JPEG compatibility)
        if img.mode in ('RGBA', 'LA', 'P'):
            # Create a white background
            background = Image.new('RGB', img.size, (255, 255, 255))
            if img.mode == 'P':
                img = img.convert('RGBA')
            background.paste(img, mask=img.split()[-1] if img.mode == 'RGBA' else None)
            img = background
        elif img.mode != 'RGB':
            img = img.convert('RGB')
        
        # Get the original format
        original_format = img.format or 'JPEG'
        
        # Resize if not 'full' size
        if size_name in cls.SIZES:
            target_size = cls.SIZES[size_name]
            
            if maintain_aspect_ratio:
                # Calculate the aspect ratio
                img.thumbnail(target_size, Image.Resampling.LANCZOS)
            else:
                # Resize to exact dimensions
                img = img.resize(target_size, Image.Resampling.LANCZOS)
        
        # Save the optimized image to a BytesIO object
        output = BytesIO()
        quality = cls.QUALITY_SETTINGS.get(size_name, 90)
        
        # Determine the format to save in
        save_format = 'JPEG'
        if original_format in ['PNG', 'GIF', 'WEBP']:
            save_format = original_format
        
        # Save with optimization
        save_kwargs = {
            'format': save_format,
            'optimize': True,
        }
        
        # Add quality setting for JPEG
        if save_format == 'JPEG':
            save_kwargs['quality'] = quality
            save_kwargs['progressive'] = True  # Enable progressive JPEG
        
        img.save(output, **save_kwargs)
        output.seek(0)
        
        return ContentFile(output.read())
    
    @classmethod
    def generate_filename(cls, original_filename, size_name):
        """
        Generate a filename for the optimized version.
        
        Args:
            original_filename: Original filename
            size_name: Size variant name
            
        Returns:
            str: New filename with size suffix
        """
        name, ext = os.path.splitext(original_filename)
        
        # Convert to .jpg for non-PNG formats when optimizing
        if size_name != 'full' and ext.lower() not in ['.png', '.gif', '.webp']:
            ext = '.jpg'
        
        if size_name == 'full':
            return f"{name}{ext}"
        
        return f"{name}_{size_name}{ext}"
    
    @classmethod
    def process_uploaded_image(cls, image_file, filename=None):
        """
        Process an uploaded image and create all size variants.
        
        Args:
            image_file: Uploaded image file
            filename: Optional custom filename
            
        Returns:
            dict: Dictionary with size names as keys and ContentFile objects as values
        """
        if not filename:
            filename = image_file.name
        
        variants = {}
        
        # Process each size variant
        for size_name in ['thumbnail', 'small', 'medium', 'large', 'full']:
            # Reset file pointer
            image_file.seek(0)
            
            # Optimize the image
            optimized = cls.optimize_image(image_file, size_name)
            
            # Generate filename for this variant
            variant_filename = cls.generate_filename(filename, size_name)
            optimized.name = variant_filename
            
            variants[size_name] = optimized
        
        return variants
