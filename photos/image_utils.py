from PIL import Image, ImageFilter, ImageStat, ImageOps
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
import numpy as np


@contextmanager
def reset_file_pointer(file_obj):
    """
    Context manager to automatically reset file pointer.
    
    Usage:
        with reset_file_pointer(image_file) as f:
            img = Image.open(f)
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
            # Check for specific non-serializable types
            if isinstance(value, (tuple, bytes, bytearray)):
                serializable[key] = str(value)
            else:
                try:
                    json.dumps(value)  # Test if serializable
                    serializable[key] = value
                except (TypeError, ValueError):
                    serializable[key] = str(value)  # Convert non-serializable to string
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
            
            exif_data = img._getexif() if hasattr(img, '_getexif') else None
            
            if not exif_data:
                return {}
            
            readable_exif = {}
            for tag_id, value in exif_data.items():
                tag = TAGS.get(tag_id, tag_id)
                readable_exif[tag] = value
            
            extracted_data = {
                'full_exif': readable_exif,
                'camera_make': readable_exif.get('Make', '').strip() if 'Make' in readable_exif else '',
                'camera_model': readable_exif.get('Model', '').strip() if 'Model' in readable_exif else '',
                'lens_model': readable_exif.get('LensModel', '').strip() if 'LensModel' in readable_exif else '',
                'iso': readable_exif.get('ISOSpeedRatings') or readable_exif.get('ISO'),
                'date_taken': ExifExtractor._parse_datetime(readable_exif.get('DateTimeOriginal') or readable_exif.get('DateTime')),
            }
            
            focal_length = readable_exif.get('FocalLength')
            if focal_length:
                extracted_data['focal_length'] = ExifExtractor._format_focal_length(focal_length)
            
            aperture = readable_exif.get('FNumber') or readable_exif.get('ApertureValue')
            if aperture:
                extracted_data['aperture'] = ExifExtractor._format_aperture(aperture)
            
            shutter_speed = readable_exif.get('ExposureTime') or readable_exif.get('ShutterSpeedValue')
            if shutter_speed:
                extracted_data['shutter_speed'] = ExifExtractor._format_shutter_speed(shutter_speed)
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
            return datetime.strptime(datetime_str, '%Y:%m:%d %H:%M:%S')  # EXIF format: 'YYYY:MM:DD HH:MM:SS'
        except (ValueError, TypeError):
            return None
    
    @staticmethod
    def _format_focal_length(focal_length):
        """Format focal length value."""
        try:
            if isinstance(focal_length, tuple):
                if focal_length[1] == 0:
                    return str(focal_length)
                value = focal_length[0] / focal_length[1]
            else:
                value = float(focal_length)
            
            if value == int(value):  # Format as integer if whole number
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
                if aperture[1] == 0:
                    return str(aperture)
                value = aperture[0] / aperture[1]
            else:
                value = float(aperture)
            
            return f"f/{value:.1f}"
        except:
            return str(aperture)
    
    @staticmethod
    def _format_shutter_speed(shutter_speed):
        """Format shutter speed value."""
        try:
            if isinstance(shutter_speed, tuple):
                numerator = shutter_speed[0]
                denominator = shutter_speed[1]
                
                if denominator == 0:
                    return str(shutter_speed)
                
                if numerator < denominator:  # Less than 1 second - show as fraction
                    from math import gcd
                    common = gcd(numerator, denominator)
                    return f"{numerator//common}/{denominator//common}"
                else:  # 1 second or more - show as decimal
                    value = numerator / denominator
                    if value == int(value):
                        return f"{int(value)}s"
                    else:
                        return f"{value:.1f}s"
            else:
                value = float(shutter_speed)
                if value < 1:
                    return f"1/{int(1/value)}"  # Convert to fraction format
                else:
                    return f"{value:.1f}s"
        except:
            return str(shutter_speed)
    
    @staticmethod
    def _extract_gps(gps_info):
        """Extract GPS coordinates from EXIF GPS info."""
        gps_data = {}
        
        try:
            gps_readable = {}
            for tag_id, value in gps_info.items():
                tag = GPSTAGS.get(tag_id, tag_id)
                gps_readable[tag] = value
            
            lat = gps_readable.get('GPSLatitude')
            lat_ref = gps_readable.get('GPSLatitudeRef')
            if lat and lat_ref:
                lat_decimal = ExifExtractor._convert_to_degrees(lat)
                if lat_ref == 'S':
                    lat_decimal = -lat_decimal
                gps_data['gps_latitude'] = Decimal(str(lat_decimal))
            
            lon = gps_readable.get('GPSLongitude')
            lon_ref = gps_readable.get('GPSLongitudeRef')
            if lon and lon_ref:
                lon_decimal = ExifExtractor._convert_to_degrees(lon)
                if lon_ref == 'W':
                    lon_decimal = -lon_decimal
                gps_data['gps_longitude'] = Decimal(str(lon_decimal))
            alt = gps_readable.get('GPSAltitude')
            alt_ref = gps_readable.get('GPSAltitudeRef')
            if alt:
                if isinstance(alt, tuple):
                    alt_value = alt[0] / alt[1] if alt[1] != 0 else 0
                else:
                    alt_value = float(alt)
                
                if alt_ref == 1:  # Below sea level
                    alt_value = -alt_value
                
                gps_data['gps_altitude'] = Decimal(str(alt_value))
            
        except Exception as e:
            print(f"Error extracting GPS data: {e}")
        
        return gps_data
    
    @staticmethod
    def _convert_to_degrees(value):
        """Convert GPS coordinates to decimal degrees."""
        try:
            # Format: ((degrees, 1), (minutes, 1), (seconds, divisor))
            d = value[0][0] / value[0][1] if value[0][1] != 0 else 0
            m = value[1][0] / value[1][1] if value[1][1] != 0 else 0
            s = value[2][0] / value[2][1] if value[2][1] != 0 else 0
            
            return d + (m / 60.0) + (s / 3600.0)
        except:
            return 0


class SmartCrop:
    """
    Smart cropping functionality to find the most interesting part of an image.
    Uses edge detection, entropy analysis, and face detection (if available).
    """
    
    @staticmethod
    def find_focal_point(img):
        """
        Find the focal point of an image using various techniques.
        
        Returns:
            tuple: (x, y) coordinates of the focal point as percentages (0-1)
        """
        if img.mode != 'RGB':
            img = img.convert('RGB')
        
        edge_point = SmartCrop._edge_detection_focal_point(img)
        entropy_point = SmartCrop._entropy_focal_point(img)
        
        # Weight: Entropy (0.7) is more reliable than edge detection (0.3) for general images
        x = (edge_point[0] * 0.3 + entropy_point[0] * 0.7)
        y = (edge_point[1] * 0.3 + entropy_point[1] * 0.7)
        
        return (x, y)
    
    @staticmethod
    def _edge_detection_focal_point(img):
        """
        Find focal point using edge detection.
        """
        gray = img.convert('L')
        edges = gray.filter(ImageFilter.FIND_EDGES)
        edges = edges.filter(ImageFilter.GaussianBlur(radius=2))
        edge_array = np.array(edges)
        
        # Find center of mass of edges
        height, width = edge_array.shape
        y_coords, x_coords = np.ogrid[:height, :width]
        
        total_weight = np.sum(edge_array)
        if total_weight == 0:
            return (0.5, 0.5)  # Center if no edges found
        
        x_center = np.sum(x_coords * edge_array) / total_weight
        y_center = np.sum(y_coords * edge_array) / total_weight
        return (x_center / width, y_center / height)
    
    @staticmethod
    def _entropy_focal_point(img, grid_size=10):
        """
        Find focal point using entropy (information density).
        Areas with more detail/texture have higher entropy.
        """
        width, height = img.size
        cell_width = width // grid_size
        cell_height = height // grid_size
        
        # If image is too small for grid analysis, return center
        if cell_width < 2 or cell_height < 2:
            return (0.5, 0.5)
        
        max_entropy = 0
        best_x, best_y = width // 2, height // 2
        
        # Ensure step size is at least 1
        step_x = max(1, cell_width // 2)
        step_y = max(1, cell_height // 2)
        
        for y in range(0, height - cell_height, step_y):
            for x in range(0, width - cell_width, step_x):
                box = (x, y, x + cell_width, y + cell_height)
                region = img.crop(box)
                entropy = SmartCrop._calculate_entropy(region)
                
                if entropy > max_entropy:
                    max_entropy = entropy
                    best_x = x + cell_width // 2
                    best_y = y + cell_height // 2
        
        return (best_x / width, best_y / height)
    
    @staticmethod
    def _calculate_entropy(img):
        """
        Calculate the entropy of an image region.
        Higher entropy means more information/detail.
        """
        if img.mode != 'L':
            img = img.convert('L')
        
        histogram = img.histogram()
        entropy = 0
        total_pixels = sum(histogram)
        
        for count in histogram:
            if count > 0:
                probability = count / total_pixels
                entropy -= probability * np.log2(probability)
        
        return entropy
    
    @staticmethod
    def smart_crop(img, target_width, target_height, focal_point=None):
        """
        Crop an image smartly to target dimensions, centering on the focal point.
        
        Args:
            img: PIL Image object
            target_width: Target width
            target_height: Target height
            focal_point: Optional (x, y) focal point as percentages (0-1)
        
        Returns:
            PIL Image: Cropped image
        """
        width, height = img.size
        target_aspect = target_width / target_height
        current_aspect = width / height
        
        if focal_point is None:
            focal_point = SmartCrop.find_focal_point(img)
        
        # Convert focal point from percentages to pixels
        focal_x = int(focal_point[0] * width)
        focal_y = int(focal_point[1] * height)
        
        if current_aspect > target_aspect:
            # Image is wider than target - crop width
            new_width = int(height * target_aspect)
            new_height = height
        else:
            # Image is taller than target - crop height
            new_width = width
            new_height = int(width / target_aspect)
        
        left = focal_x - new_width // 2
        top = focal_y - new_height // 2
        left = max(0, min(left, width - new_width))
        top = max(0, min(top, height - new_height))
        right = left + new_width
        bottom = top + new_height
        
        cropped = img.crop((left, top, right, bottom))
        cropped = cropped.resize((target_width, target_height), Image.Resampling.LANCZOS)
        
        return cropped


class ImageOptimizer:
    """
    Handles image optimization and resizing for different use cases.
    """
    
    # Define size presets for different use cases
    SIZES = {
        'display': (1200, 800),  # Smart-cropped display version for gallery
        'optimized': None,  # Full size but compressed
        # 'original' will be the untouched original
    }
    
    # Quality settings for JPEG compression
    QUALITY_SETTINGS = {
        'display': 85,  # Good quality for display
        'optimized': 90,  # High quality but compressed
        'original': 100,  # No compression
    }
    
    @classmethod
    def optimize_image(cls, image_file, size_name='original', maintain_aspect_ratio=True, use_smart_crop=True, focal_point=None):
        """
        Optimize an image file for a specific size.
        
        Args:
            image_file: Django ImageField file or file-like object
            size_name: One of 'display', 'optimized', or 'original'
            maintain_aspect_ratio: If True, maintains aspect ratio when resizing
            use_smart_crop: If True and size_name is 'display', use smart cropping
            focal_point: Optional (x, y) focal point as percentages (0-1)
            
        Returns:
            tuple: (ContentFile: Optimized image, focal_point: (x, y) or None)
        """
        if size_name == 'original':
            image_file.seek(0)
            return (ContentFile(image_file.read()), None)
        img = Image.open(image_file)
        computed_focal_point = None
        
        if img.mode in ('RGBA', 'LA', 'P'):
            background = Image.new('RGB', img.size, (255, 255, 255))
            if img.mode == 'P':
                img = img.convert('RGBA')
            background.paste(img, mask=img.split()[-1] if img.mode == 'RGBA' else None)
            img = background
        elif img.mode != 'RGB':
            img = img.convert('RGB')
        
        original_format = img.format or 'JPEG'
        
        if size_name == 'optimized':
            pass  # Just compress without resizing
        elif size_name in cls.SIZES and cls.SIZES[size_name]:
            target_size = cls.SIZES[size_name]
            
            if use_smart_crop and size_name == 'display':
                if focal_point is None:
                    computed_focal_point = SmartCrop.find_focal_point(img)
                else:
                    computed_focal_point = focal_point
                
                img = SmartCrop.smart_crop(img, target_size[0], target_size[1], computed_focal_point)
            elif maintain_aspect_ratio:
                img.thumbnail(target_size, Image.Resampling.LANCZOS)
            else:
                img = img.resize(target_size, Image.Resampling.LANCZOS)
        output = BytesIO()
        quality = cls.QUALITY_SETTINGS.get(size_name, 90)
        
        save_format = 'JPEG'
        if original_format in ['PNG', 'GIF', 'WEBP']:
            save_format = original_format
        save_kwargs = {
            'format': save_format,
            'optimize': True,
        }
        
        if save_format == 'JPEG':
            save_kwargs['quality'] = quality
            save_kwargs['progressive'] = True  # Progressive JPEG for better web loading
        
        img.save(output, **save_kwargs)
        output.seek(0)
        
        return (ContentFile(output.read()), computed_focal_point)
    
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
        
        if size_name != 'original' and ext.lower() not in ['.png', '.gif', '.webp']:
            ext = '.jpg'  # Convert to .jpg when optimizing (except PNG/GIF/WebP)
        
        if size_name == 'original':
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
            tuple: (variants dict, focal_point tuple or None)
        """
        if not filename:
            filename = image_file.name
        
        variants = {}
        focal_point = None
        
        for size_name in ['display', 'optimized']:
            image_file.seek(0)
            optimized, computed_focal = cls.optimize_image(image_file, size_name, focal_point=focal_point)
            
            # Store focal point from first computation (display version)
            if computed_focal and not focal_point:
                focal_point = computed_focal
            
            variant_filename = cls.generate_filename(filename, size_name)
            optimized.name = variant_filename
            variants[size_name] = optimized
        
        return (variants, focal_point)


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
            if algorithm == 'md5':
                hasher = hashlib.md5()
            elif algorithm == 'sha1':
                hasher = hashlib.sha1()
            else:  # Default to sha256
                hasher = hashlib.sha256()
            
            image_file.seek(0)
            
            # Read in 8KB chunks for memory efficiency with large files
            for chunk in iter(lambda: image_file.read(8192), b''):
                hasher.update(chunk)
            
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
            image_file.seek(0)
            img = Image.open(image_file)
            
            if img.mode not in ('RGB', 'L'):
                if img.mode == 'RGBA':
                    background = Image.new('RGB', img.size, (255, 255, 255))
                    background.paste(img, mask=img.split()[-1])
                    img = background
                else:
                    img = img.convert('RGB')
            
            # Average hash algorithm - good balance of speed and accuracy
            phash = imagehash.average_hash(img, hash_size=hash_size)
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
            image_file.seek(0)
            img = Image.open(image_file)
            
            if img.mode not in ('RGB', 'L'):
                if img.mode == 'RGBA':
                    background = Image.new('RGB', img.size, (255, 255, 255))
                    background.paste(img, mask=img.split()[-1])
                    img = background
                else:
                    img = img.convert('RGB')
            
            # Multiple hash types for comprehensive comparison
            hashes = {
                'average': str(imagehash.average_hash(img)),
                'perceptual': str(imagehash.phash(img)),
                'difference': str(imagehash.dhash(img)),
                'wavelet': str(imagehash.whash(img)),
            }
            
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
            h1 = imagehash.hex_to_hash(hash1)
            h2 = imagehash.hex_to_hash(hash2)
            distance = h1 - h2  # Hamming distance
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
            file_hash = DuplicateDetector.compute_file_hash(image_file)
            result['file_hash'] = file_hash
            
            if not exact_match_only:
                perceptual_hash = DuplicateDetector.compute_perceptual_hash(image_file)
                result['perceptual_hash'] = perceptual_hash
            
            if file_hash:
                exact_matches = existing_photos_queryset.filter(file_hash=file_hash)
                result['exact_duplicates'] = list(exact_matches)
            
            if not exact_match_only and perceptual_hash:
                photos_with_hashes = existing_photos_queryset.exclude(
                    perceptual_hash__isnull=True
                ).exclude(
                    perceptual_hash=''
                )
                
                for photo in photos_with_hashes:
                    is_similar, distance = DuplicateDetector.compare_hashes(
                        perceptual_hash,
                        photo.perceptual_hash,
                        threshold=5
                    )
                    
                    if is_similar and photo not in result['exact_duplicates']:
                        result['similar_images'].append((photo, distance))
                
                # Sort by similarity score (lower distance = more similar)
                result['similar_images'].sort(key=lambda x: x[1])
            
        except Exception as e:
            print(f"Error finding duplicates: {e}")
        
        return result
