"""
Image processing utilities for optimizing images before uploading to S3.
"""
from PIL import Image
from PIL.ExifTags import TAGS, GPSTAGS
from io import BytesIO
from django.core.files.base import ContentFile
from datetime import datetime
from decimal import Decimal
from contextlib import contextmanager
import os
import json
import hashlib
import imagehash


@contextmanager
def reset_file_pointer(file_obj):
    """
    Context manager to automatically reset file pointer.
    
    Usage:
        with reset_file_pointer(image_file) as f:
            # Do operations with the file
            img = Image.open(f)
            # File pointer will be automatically reset when exiting
    """
    initial_position = file_obj.tell() if hasattr(file_obj, 'tell') else 0
    try:
        yield file_obj
    finally:
        if hasattr(file_obj, 'seek'):
            file_obj.seek(initial_position)


class ImageMetadataExtractor:
    """
    Extracts basic metadata from images without EXIF processing.
    """
    
    @staticmethod
    def extract_basic_metadata(image_file):
        """
        Extract basic metadata like dimensions and file size.
        
        Args:
            image_file: Django ImageField file or file-like object
            
        Returns:
            dict: Dictionary containing width, height, file_size, and format
        """
        with reset_file_pointer(image_file):
            img = Image.open(image_file)
            metadata = {
                'width': img.width,
                'height': img.height,
                'file_size': image_file.size if hasattr(image_file, 'size') else None,
                'format': img.format,
                'mode': img.mode
            }
            return metadata


class ExifExtractor:
    """
    Extracts and processes EXIF data from images.
    """
    
    @staticmethod
    def make_exif_serializable(exif_data):
        """
        Convert EXIF data to JSON-serializable format.
        
        Args:
            exif_data: Dictionary containing EXIF data with potentially non-serializable values
            
        Returns:
            dict: JSON-serializable version of the EXIF data
        """
        serializable = {}
        for key, value in exif_data.items():
            try:
                # Try to serialize the value
                json.dumps(value)
                serializable[key] = value
            except (TypeError, ValueError):
                # If not serializable, convert to string
                serializable[key] = str(value)
        return serializable
    
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


class DuplicateDetector:
    """
    Handles duplicate image detection using various hashing methods.
    """
    
    @staticmethod
    def compute_and_store_hashes(image_file):
        """
        Compute both file and perceptual hashes in one operation.
        
        Args:
            image_file: Django ImageField file or file-like object
            
        Returns:
            dict: Dictionary containing 'file_hash' and 'perceptual_hash'
        """
        return {
            'file_hash': DuplicateDetector.compute_file_hash(image_file),
            'perceptual_hash': DuplicateDetector.compute_perceptual_hash(image_file)
        }
    
    @staticmethod
    def compute_file_hash(image_file, algorithm='sha256'):
        """
        Compute cryptographic hash of image file for exact duplicate detection.
        
        Args:
            image_file: Django ImageField file or file-like object
            algorithm: Hash algorithm to use ('md5', 'sha1', 'sha256')
            
        Returns:
            str: Hexadecimal hash string
        """
        try:
            # Choose hash algorithm
            if algorithm == 'md5':
                hasher = hashlib.md5()
            elif algorithm == 'sha1':
                hasher = hashlib.sha1()
            else:  # Default to sha256
                hasher = hashlib.sha256()
            
            # Reset file pointer
            image_file.seek(0)
            
            # Read file in chunks to handle large files efficiently
            for chunk in iter(lambda: image_file.read(8192), b''):
                hasher.update(chunk)
            
            # Reset file pointer after reading
            image_file.seek(0)
            
            return hasher.hexdigest()
        except Exception as e:
            print(f"Error computing file hash: {e}")
            return None
    
    @staticmethod
    def compute_perceptual_hash(image_file, hash_size=16):
        """
        Compute perceptual hash for similar image detection.
        This can detect images that are visually similar even if they've been:
        - Resized
        - Compressed differently
        - Slightly color-adjusted
        - Had minor edits
        
        Args:
            image_file: Django ImageField file or file-like object
            hash_size: Size of the hash (higher = more precise, but less tolerant to changes)
            
        Returns:
            str: Hexadecimal perceptual hash string
        """
        try:
            # Reset file pointer
            image_file.seek(0)
            
            # Open image with PIL
            img = Image.open(image_file)
            
            # Convert to RGB if necessary
            if img.mode not in ('RGB', 'L'):
                if img.mode == 'RGBA':
                    # Create white background for RGBA images
                    background = Image.new('RGB', img.size, (255, 255, 255))
                    background.paste(img, mask=img.split()[-1])
                    img = background
                else:
                    img = img.convert('RGB')
            
            # Compute perceptual hash using average hash algorithm
            # You can also use dhash, phash, or whash for different characteristics
            phash = imagehash.average_hash(img, hash_size=hash_size)
            
            # Reset file pointer after processing
            image_file.seek(0)
            
            return str(phash)
        except Exception as e:
            print(f"Error computing perceptual hash: {e}")
            return None
    
    @staticmethod
    def compute_multiple_hashes(image_file):
        """
        Compute multiple types of perceptual hashes for comprehensive comparison.
        
        Args:
            image_file: Django ImageField file or file-like object
            
        Returns:
            dict: Dictionary containing different hash types
        """
        try:
            # Reset file pointer
            image_file.seek(0)
            
            # Open image with PIL
            img = Image.open(image_file)
            
            # Convert to RGB if necessary
            if img.mode not in ('RGB', 'L'):
                if img.mode == 'RGBA':
                    background = Image.new('RGB', img.size, (255, 255, 255))
                    background.paste(img, mask=img.split()[-1])
                    img = background
                else:
                    img = img.convert('RGB')
            
            # Compute different types of hashes
            hashes = {
                'average': str(imagehash.average_hash(img)),
                'perceptual': str(imagehash.phash(img)),
                'difference': str(imagehash.dhash(img)),
                'wavelet': str(imagehash.whash(img)),
            }
            
            # Reset file pointer after processing
            image_file.seek(0)
            
            return hashes
        except Exception as e:
            print(f"Error computing multiple hashes: {e}")
            return {}
    
    @staticmethod
    def compare_hashes(hash1, hash2, threshold=5):
        """
        Compare two perceptual hashes to determine similarity.
        
        Args:
            hash1: First perceptual hash (string)
            hash2: Second perceptual hash (string)
            threshold: Maximum Hamming distance for considering images similar
                      (lower = more strict, typical range: 0-10)
            
        Returns:
            tuple: (is_similar: bool, distance: int)
        """
        try:
            # Convert strings back to ImageHash objects
            h1 = imagehash.hex_to_hash(hash1)
            h2 = imagehash.hex_to_hash(hash2)
            
            # Calculate Hamming distance
            distance = h1 - h2
            
            # Determine if images are similar based on threshold
            is_similar = distance <= threshold
            
            return is_similar, distance
        except Exception as e:
            print(f"Error comparing hashes: {e}")
            return False, float('inf')
    
    @staticmethod
    def find_duplicates(image_file, existing_photos_queryset, exact_match_only=False):
        """
        Find duplicate or similar images in the database.
        
        Args:
            image_file: Image file to check for duplicates
            existing_photos_queryset: QuerySet of Photo objects to check against
            exact_match_only: If True, only check for exact file duplicates
            
        Returns:
            dict: {
                'exact_duplicates': [list of Photo objects with identical file hash],
                'similar_images': [list of (Photo, similarity_score) tuples],
                'file_hash': computed file hash of the input image,
                'perceptual_hash': computed perceptual hash of the input image
            }
        """
        result = {
            'exact_duplicates': [],
            'similar_images': [],
            'file_hash': None,
            'perceptual_hash': None
        }
        
        try:
            # Compute hashes for the uploaded image
            file_hash = DuplicateDetector.compute_file_hash(image_file)
            result['file_hash'] = file_hash
            
            if not exact_match_only:
                perceptual_hash = DuplicateDetector.compute_perceptual_hash(image_file)
                result['perceptual_hash'] = perceptual_hash
            
            # Check for exact duplicates by file hash
            if file_hash:
                exact_matches = existing_photos_queryset.filter(file_hash=file_hash)
                result['exact_duplicates'] = list(exact_matches)
            
            # Check for similar images by perceptual hash
            if not exact_match_only and perceptual_hash:
                # Get all photos with perceptual hashes
                photos_with_hashes = existing_photos_queryset.exclude(
                    perceptual_hash__isnull=True
                ).exclude(
                    perceptual_hash=''
                )
                
                for photo in photos_with_hashes:
                    is_similar, distance = DuplicateDetector.compare_hashes(
                        perceptual_hash,
                        photo.perceptual_hash,
                        threshold=5  # Adjust threshold as needed
                    )
                    
                    if is_similar and photo not in result['exact_duplicates']:
                        # Store photo with similarity score (lower distance = more similar)
                        result['similar_images'].append((photo, distance))
                
                # Sort similar images by similarity (lowest distance first)
                result['similar_images'].sort(key=lambda x: x[1])
            
        except Exception as e:
            print(f"Error finding duplicates: {e}")
        
        return result
