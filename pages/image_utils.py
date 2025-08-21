"""
Image processing utilities for optimizing images before uploading to S3.
"""
from PIL import Image
from PIL.ExifTags import TAGS, GPSTAGS
from io import BytesIO
from django.core.files.base import ContentFile
from datetime import datetime
from decimal import Decimal
import os
import json


class ExifExtractor:
    """
    Extracts and processes EXIF data from images.
    """
    
    @staticmethod
    def extract_exif(image_file):
        """
        Extract EXIF data from an image file.
        
        Args:
            image_file: Django ImageField file or file-like object
            
        Returns:
            dict: Dictionary containing extracted EXIF data
        """
        try:
            image_file.seek(0)
            img = Image.open(image_file)
            
            # Get basic EXIF data
            exif_data = img._getexif() if hasattr(img, '_getexif') else None
            
            if not exif_data:
                return {}
            
            # Convert EXIF data to readable format
            readable_exif = {}
            for tag_id, value in exif_data.items():
                tag = TAGS.get(tag_id, tag_id)
                readable_exif[tag] = value
            
            # Extract specific fields
            extracted_data = {
                'full_exif': readable_exif,  # Store complete EXIF data
                'camera_make': readable_exif.get('Make', '').strip() if 'Make' in readable_exif else '',
                'camera_model': readable_exif.get('Model', '').strip() if 'Model' in readable_exif else '',
                'lens_model': readable_exif.get('LensModel', '').strip() if 'LensModel' in readable_exif else '',
                'iso': readable_exif.get('ISOSpeedRatings') or readable_exif.get('ISO'),
                'date_taken': ExifExtractor._parse_datetime(readable_exif.get('DateTimeOriginal') or readable_exif.get('DateTime')),
            }
            
            # Extract focal length
            focal_length = readable_exif.get('FocalLength')
            if focal_length:
                extracted_data['focal_length'] = ExifExtractor._format_focal_length(focal_length)
            
            # Extract aperture
            aperture = readable_exif.get('FNumber') or readable_exif.get('ApertureValue')
            if aperture:
                extracted_data['aperture'] = ExifExtractor._format_aperture(aperture)
            
            # Extract shutter speed
            shutter_speed = readable_exif.get('ExposureTime') or readable_exif.get('ShutterSpeedValue')
            if shutter_speed:
                extracted_data['shutter_speed'] = ExifExtractor._format_shutter_speed(shutter_speed)
            
            # Extract GPS data
            gps_info = readable_exif.get('GPSInfo')
            if gps_info:
                gps_data = ExifExtractor._extract_gps(gps_info)
                extracted_data.update(gps_data)
            
            return extracted_data
            
        except Exception as e:
            print(f"Error extracting EXIF data: {e}")
            return {}
    
    @staticmethod
    def _parse_datetime(datetime_str):
        """Parse EXIF datetime string to Python datetime object."""
        if not datetime_str:
            return None
        try:
            # EXIF datetime format is typically 'YYYY:MM:DD HH:MM:SS'
            return datetime.strptime(datetime_str, '%Y:%m:%d %H:%M:%S')
        except (ValueError, TypeError):
            return None
    
    @staticmethod
    def _format_focal_length(focal_length):
        """Format focal length value."""
        try:
            if isinstance(focal_length, tuple):
                # Handle rational number format (numerator, denominator)
                value = focal_length[0] / focal_length[1] if focal_length[1] != 0 else 0
            else:
                value = float(focal_length)
            
            # Format as integer if it's a whole number, otherwise with one decimal
            if value == int(value):
                return f"{int(value)}mm"
            else:
                return f"{value:.1f}mm"
        except:
            return str(focal_length)
    
    @staticmethod
    def _format_aperture(aperture):
        """Format aperture value."""
        try:
            if isinstance(aperture, tuple):
                # Handle rational number format
                value = aperture[0] / aperture[1] if aperture[1] != 0 else 0
            else:
                value = float(aperture)
            
            # Format with one decimal place
            return f"f/{value:.1f}"
        except:
            return str(aperture)
    
    @staticmethod
    def _format_shutter_speed(shutter_speed):
        """Format shutter speed value."""
        try:
            if isinstance(shutter_speed, tuple):
                # Handle rational number format
                numerator = shutter_speed[0]
                denominator = shutter_speed[1]
                
                if denominator == 0:
                    return str(shutter_speed)
                
                # If exposure time is less than 1 second, show as fraction
                if numerator < denominator:
                    # Simplify the fraction if possible
                    from math import gcd
                    common = gcd(numerator, denominator)
                    return f"{numerator//common}/{denominator//common}"
                else:
                    # Show as decimal seconds
                    value = numerator / denominator
                    if value == int(value):
                        return f"{int(value)}s"
                    else:
                        return f"{value:.1f}s"
            else:
                value = float(shutter_speed)
                if value < 1:
                    # Convert to fraction format
                    return f"1/{int(1/value)}"
                else:
                    return f"{value:.1f}s"
        except:
            return str(shutter_speed)
    
    @staticmethod
    def _extract_gps(gps_info):
        """Extract GPS coordinates from EXIF GPS info."""
        gps_data = {}
        
        try:
            # Convert GPS tag IDs to names
            gps_readable = {}
            for tag_id, value in gps_info.items():
                tag = GPSTAGS.get(tag_id, tag_id)
                gps_readable[tag] = value
            
            # Extract latitude
            lat = gps_readable.get('GPSLatitude')
            lat_ref = gps_readable.get('GPSLatitudeRef')
            if lat and lat_ref:
                lat_decimal = ExifExtractor._convert_to_degrees(lat)
                if lat_ref == 'S':
                    lat_decimal = -lat_decimal
                gps_data['gps_latitude'] = Decimal(str(lat_decimal))
            
            # Extract longitude
            lon = gps_readable.get('GPSLongitude')
            lon_ref = gps_readable.get('GPSLongitudeRef')
            if lon and lon_ref:
                lon_decimal = ExifExtractor._convert_to_degrees(lon)
                if lon_ref == 'W':
                    lon_decimal = -lon_decimal
                gps_data['gps_longitude'] = Decimal(str(lon_decimal))
            
            # Extract altitude
            alt = gps_readable.get('GPSAltitude')
            alt_ref = gps_readable.get('GPSAltitudeRef')
            if alt:
                if isinstance(alt, tuple):
                    alt_value = alt[0] / alt[1] if alt[1] != 0 else 0
                else:
                    alt_value = float(alt)
                
                # Below sea level if alt_ref is 1
                if alt_ref == 1:
                    alt_value = -alt_value
                
                gps_data['gps_altitude'] = Decimal(str(alt_value))
            
        except Exception as e:
            print(f"Error extracting GPS data: {e}")
        
        return gps_data
    
    @staticmethod
    def _convert_to_degrees(value):
        """Convert GPS coordinates to decimal degrees."""
        try:
            # GPS coordinates are stored as ((degrees, 1), (minutes, 1), (seconds, divisor))
            d = value[0][0] / value[0][1] if value[0][1] != 0 else 0
            m = value[1][0] / value[1][1] if value[1][1] != 0 else 0
            s = value[2][0] / value[2][1] if value[2][1] != 0 else 0
            
            return d + (m / 60.0) + (s / 3600.0)
        except:
            return 0


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
