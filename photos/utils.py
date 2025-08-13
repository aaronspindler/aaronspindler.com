"""
Utility functions for image processing and validation with enhanced error handling and type hints.
"""
import os
import logging
from typing import Optional, Tuple, Union, BinaryIO
from PIL import Image, ImageOps, UnidentifiedImageError
from io import BytesIO
from django.core.files.base import ContentFile, File
from django.core.files.uploadedfile import UploadedFile, InMemoryUploadedFile
from django.conf import settings
from django.core.exceptions import ValidationError

# Set up logger
logger = logging.getLogger(__name__)

# Constants for image processing
DEFAULT_THUMBNAIL_SIZE: Tuple[int, int] = (400, 400)
DEFAULT_THUMBNAIL_QUALITY: int = 85
MAX_IMAGE_SIZE: int = 10 * 1024 * 1024  # 10MB
MAX_IMAGE_DIMENSION: int = 4000
VALID_IMAGE_EXTENSIONS: list[str] = ['.jpg', '.jpeg', '.png', '.gif', '.webp']
VALID_IMAGE_FORMATS: dict[str, str] = {
    '.jpg': 'JPEG',
    '.jpeg': 'JPEG',
    '.png': 'PNG',
    '.gif': 'GIF',
    '.webp': 'WEBP'
}


def generate_thumbnail(
    image_file: Union[File, BinaryIO, UploadedFile],
    size: Optional[Tuple[int, int]] = None,
    quality: Optional[int] = None
) -> Optional[ContentFile]:
    """
    Generate a thumbnail from an image file with comprehensive error handling.
    
    Args:
        image_file: Django ImageField file object or file-like object
        size: Tuple of (width, height) for thumbnail, defaults to settings or (400, 400)
        quality: JPEG quality (1-100), defaults to settings or 85
    
    Returns:
        ContentFile: Thumbnail image as a ContentFile ready to be saved
        None: If thumbnail generation fails
        
    Raises:
        None: All exceptions are caught and logged
    """
    if size is None:
        size = getattr(settings, 'THUMBNAIL_SIZE', DEFAULT_THUMBNAIL_SIZE)
    
    if quality is None:
        quality = getattr(settings, 'THUMBNAIL_QUALITY', DEFAULT_THUMBNAIL_QUALITY)
    
    # Validate parameters
    if not isinstance(size, tuple) or len(size) != 2:
        logger.error(f"Invalid thumbnail size: {size}")
        return None
    
    if not isinstance(quality, int) or quality < 1 or quality > 100:
        logger.error(f"Invalid thumbnail quality: {quality}")
        quality = DEFAULT_THUMBNAIL_QUALITY
    
    try:
        logger.debug(f"Generating thumbnail with size {size} and quality {quality}")
        
        # Reset file pointer if possible
        if hasattr(image_file, 'seek'):
            image_file.seek(0)
        
        # Open the image
        try:
            img = Image.open(image_file)
        except UnidentifiedImageError as e:
            logger.error(f"Cannot identify image format: {str(e)}")
            return None
        except Exception as e:
            logger.error(f"Failed to open image: {str(e)}")
            return None
        
        # Verify image is valid
        try:
            img.verify()
            # Need to reopen after verify
            if hasattr(image_file, 'seek'):
                image_file.seek(0)
            img = Image.open(image_file)
        except Exception as e:
            logger.error(f"Image verification failed: {str(e)}")
            return None
        
        # Log original image info
        logger.debug(f"Original image: mode={img.mode}, size={img.size}, format={img.format}")
        
        # Apply EXIF orientation if present
        try:
            img = ImageOps.exif_transpose(img)
        except Exception as e:
            logger.warning(f"Could not apply EXIF orientation: {str(e)}")
        
        # Convert image mode if necessary for JPEG compatibility
        if img.mode in ('RGBA', 'LA', 'P'):
            logger.debug(f"Converting image from {img.mode} to RGB")
            try:
                # Create a white background
                background = Image.new('RGB', img.size, (255, 255, 255))
                
                # Convert palette images to RGBA first
                if img.mode == 'P':
                    if 'transparency' in img.info:
                        img = img.convert('RGBA')
                    else:
                        img = img.convert('RGB')
                
                # Paste image with alpha channel if present
                if img.mode in ('RGBA', 'LA'):
                    background.paste(img, mask=img.split()[-1])
                    img = background
                elif img.mode == 'RGB':
                    img = img
                else:
                    background.paste(img)
                    img = background
                    
            except Exception as e:
                logger.error(f"Failed to convert image mode: {str(e)}")
                return None
        
        # Create thumbnail maintaining aspect ratio
        try:
            img.thumbnail(size, Image.Resampling.LANCZOS)
            logger.debug(f"Thumbnail created with size: {img.size}")
        except Exception as e:
            logger.error(f"Failed to create thumbnail: {str(e)}")
            return None
        
        # Save thumbnail to BytesIO
        thumb_io = BytesIO()
        try:
            img.save(thumb_io, format='JPEG', quality=quality, optimize=True, progressive=True)
            logger.debug(f"Thumbnail saved to buffer, size: {thumb_io.tell()} bytes")
        except Exception as e:
            logger.error(f"Failed to save thumbnail to buffer: {str(e)}")
            return None
        
        # Create ContentFile from BytesIO
        try:
            thumb_file = ContentFile(thumb_io.getvalue())
            logger.info(f"Thumbnail generated successfully, final size: {len(thumb_io.getvalue())} bytes")
            return thumb_file
        except Exception as e:
            logger.error(f"Failed to create ContentFile: {str(e)}")
            return None
        
    except Exception as e:
        logger.error(f"Unexpected error generating thumbnail: {str(e)}", exc_info=True)
        return None
    finally:
        # Reset file pointer for potential reuse
        if hasattr(image_file, 'seek'):
            try:
                image_file.seek(0)
            except:
                pass


def validate_image(
    image_file: Union[UploadedFile, File],
    max_size: Optional[int] = None,
    valid_extensions: Optional[list[str]] = None
) -> Tuple[bool, Optional[str]]:
    """
    Validate that the uploaded file is a valid image with enhanced checks.
    
    Args:
        image_file: Uploaded file object
        max_size: Maximum file size in bytes (default: 10MB)
        valid_extensions: List of valid file extensions
    
    Returns:
        tuple: (is_valid, error_message)
            - is_valid: True if image is valid, False otherwise
            - error_message: Error description if invalid, None if valid
    """
    if max_size is None:
        max_size = MAX_IMAGE_SIZE
    
    if valid_extensions is None:
        valid_extensions = VALID_IMAGE_EXTENSIONS
    
    try:
        # Check if file exists
        if not image_file:
            logger.warning("No image file provided for validation")
            return False, "No image file provided"
        
        # Check file size
        try:
            file_size = image_file.size if hasattr(image_file, 'size') else len(image_file.read())
            if hasattr(image_file, 'seek'):
                image_file.seek(0)  # Reset after reading
                
            if file_size > max_size:
                size_mb = max_size / (1024 * 1024)
                logger.warning(f"Image file too large: {file_size} bytes (max: {max_size} bytes)")
                return False, f"Image file size must be less than {size_mb:.0f}MB"
                
            if file_size == 0:
                logger.warning("Empty image file uploaded")
                return False, "Image file is empty"
                
        except Exception as e:
            logger.error(f"Error checking file size: {str(e)}")
            return False, "Could not determine file size"
        
        # Check file extension
        try:
            filename = getattr(image_file, 'name', 'unknown')
            ext = os.path.splitext(filename)[1].lower()
            
            if ext not in valid_extensions:
                logger.warning(f"Invalid file extension: {ext}")
                return False, f"Invalid file extension. Allowed: {', '.join(valid_extensions)}"
                
        except Exception as e:
            logger.error(f"Error checking file extension: {str(e)}")
            return False, "Could not determine file type"
        
        # Try to open and verify the image
        try:
            # Reset file pointer
            if hasattr(image_file, 'seek'):
                image_file.seek(0)
            
            img = Image.open(image_file)
            
            # Verify it's a valid image
            img.verify()
            
            # Get image info for logging
            if hasattr(image_file, 'seek'):
                image_file.seek(0)
                img = Image.open(image_file)
            
            width, height = img.size
            format = img.format
            
            logger.debug(f"Valid image: {filename}, size: {width}x{height}, format: {format}")
            
            # Check image dimensions
            if width == 0 or height == 0:
                logger.warning(f"Invalid image dimensions: {width}x{height}")
                return False, "Image has invalid dimensions"
            
            # Check for extremely large dimensions
            max_dim = getattr(settings, 'MAX_IMAGE_DIMENSION', MAX_IMAGE_DIMENSION * 2)
            if width > max_dim or height > max_dim:
                logger.warning(f"Image dimensions too large: {width}x{height}")
                return False, f"Image dimensions too large (max: {max_dim}x{max_dim})"
            
            # Reset file pointer for further use
            if hasattr(image_file, 'seek'):
                image_file.seek(0)
            
            logger.info(f"Image validation successful: {filename}")
            return True, None
            
        except UnidentifiedImageError as e:
            logger.error(f"Cannot identify image file: {str(e)}")
            return False, "File is not a valid image"
            
        except Exception as e:
            logger.error(f"Error validating image: {str(e)}")
            return False, f"Invalid image file: {str(e)}"
            
    except Exception as e:
        logger.error(f"Unexpected error during image validation: {str(e)}", exc_info=True)
        return False, "An unexpected error occurred during validation"


def get_thumbnail_filename(original_filename: str) -> str:
    """
    Generate a thumbnail filename from the original filename.
    
    Args:
        original_filename: Original image filename (can include path)
    
    Returns:
        str: Thumbnail filename with _thumb suffix and .jpg extension
        
    Examples:
        >>> get_thumbnail_filename("photo.jpg")
        'photo_thumb.jpg'
        >>> get_thumbnail_filename("path/to/image.png")
        'path/to/image_thumb.jpg'
    """
    try:
        if not original_filename:
            logger.warning("Empty filename provided for thumbnail generation")
            return "thumbnail_thumb.jpg"
        
        # Split path and filename
        path_parts = original_filename.rsplit('/', 1)
        if len(path_parts) == 2:
            path, filename = path_parts
        else:
            path = ""
            filename = original_filename
        
        # Split name and extension
        name_parts = filename.rsplit('.', 1)
        if len(name_parts) == 2:
            name, ext = name_parts
        else:
            name = filename
            ext = ""
        
        # Generate thumbnail filename (always use .jpg for thumbnails)
        thumb_filename = f"{name}_thumb.jpg"
        
        # Reconstruct full path if needed
        if path:
            result = f"{path}/{thumb_filename}"
        else:
            result = thumb_filename
        
        logger.debug(f"Generated thumbnail filename: {original_filename} -> {result}")
        return result
        
    except Exception as e:
        logger.error(f"Error generating thumbnail filename: {str(e)}", exc_info=True)
        return "error_thumb.jpg"


def cleanup_s3_file(file_field: Optional[Union[File, ContentFile]]) -> bool:
    """
    Delete a file from S3 storage with enhanced error handling.
    
    Args:
        file_field: Django FileField or ImageField
    
    Returns:
        bool: True if successful or file doesn't exist, False on error
    """
    if not file_field:
        logger.debug("No file to cleanup (field is empty)")
        return True
    
    try:
        file_name = getattr(file_field, 'name', None)
        
        if not file_name:
            logger.debug("No file name available for cleanup")
            return True
        
        logger.info(f"Attempting to delete S3 file: {file_name}")
        
        # Delete the file from storage
        file_field.delete(save=False)
        
        logger.info(f"Successfully deleted S3 file: {file_name}")
        return True
        
    except AttributeError as e:
        logger.warning(f"File field has no delete method: {str(e)}")
        return False
        
    except Exception as e:
        logger.error(f"Failed to delete S3 file: {str(e)}", exc_info=True)
        return False


def process_uploaded_image(
    image_file: Union[UploadedFile, File],
    max_dimension: Optional[int] = None,
    optimize: bool = True
) -> Tuple[Optional[Union[ContentFile, UploadedFile, File]], Optional[str]]:
    """
    Process an uploaded image - validate, resize if needed, and optimize.
    
    Args:
        image_file: Uploaded image file
        max_dimension: Maximum width/height (default: 4000px)
        optimize: Whether to optimize the image (default: True)
    
    Returns:
        tuple: (processed_file, error_message)
            - processed_file: Processed image or None if error
            - error_message: Error description if failed, None if successful
    """
    if max_dimension is None:
        max_dimension = getattr(settings, 'MAX_IMAGE_DIMENSION', MAX_IMAGE_DIMENSION)
    
    # Validate the image first
    is_valid, error_msg = validate_image(image_file)
    if not is_valid:
        logger.error(f"Image validation failed: {error_msg}")
        return None, error_msg
    
    try:
        logger.info(f"Processing uploaded image: {getattr(image_file, 'name', 'unknown')}")
        
        # Reset file pointer
        if hasattr(image_file, 'seek'):
            image_file.seek(0)
        
        # Open the image
        try:
            img = Image.open(image_file)
        except Exception as e:
            logger.error(f"Failed to open image for processing: {str(e)}")
            return None, f"Failed to open image: {str(e)}"
        
        # Apply EXIF orientation
        try:
            img = ImageOps.exif_transpose(img)
        except Exception as e:
            logger.warning(f"Could not apply EXIF orientation: {str(e)}")
        
        original_width, original_height = img.size
        original_format = img.format or 'JPEG'
        needs_processing = False
        
        # Check if resizing is needed
        if original_width > max_dimension or original_height > max_dimension:
            logger.info(f"Resizing image from {original_width}x{original_height} to max {max_dimension}")
            try:
                img.thumbnail((max_dimension, max_dimension), Image.Resampling.LANCZOS)
                needs_processing = True
            except Exception as e:
                logger.error(f"Failed to resize image: {str(e)}")
                return None, f"Failed to resize image: {str(e)}"
        
        # Determine output format
        filename = getattr(image_file, 'name', 'image.jpg').lower()
        
        if filename.endswith('.png'):
            output_format = 'PNG'
        elif filename.endswith('.webp'):
            output_format = 'WEBP'
        elif filename.endswith('.gif'):
            output_format = 'GIF'
        else:
            output_format = 'JPEG'
            needs_processing = True  # Always process JPEG for optimization
        
        # Convert image mode if necessary for JPEG
        if output_format == 'JPEG' and img.mode in ('RGBA', 'LA', 'P'):
            logger.debug(f"Converting image from {img.mode} to RGB for JPEG")
            try:
                background = Image.new('RGB', img.size, (255, 255, 255))
                if img.mode == 'P':
                    if 'transparency' in img.info:
                        img = img.convert('RGBA')
                    else:
                        img = img.convert('RGB')
                
                if img.mode in ('RGBA', 'LA'):
                    background.paste(img, mask=img.split()[-1])
                    img = background
                elif img.mode != 'RGB':
                    background.paste(img)
                    img = background
                    
                needs_processing = True
            except Exception as e:
                logger.error(f"Failed to convert image mode: {str(e)}")
                return None, f"Failed to convert image: {str(e)}"
        
        # If no processing needed and optimization not requested, return original
        if not needs_processing and not optimize:
            logger.debug("No processing needed, returning original image")
            if hasattr(image_file, 'seek'):
                image_file.seek(0)
            return image_file, None
        
        # Save processed image
        try:
            output_io = BytesIO()
            
            save_kwargs = {
                'format': output_format,
                'optimize': optimize
            }
            
            # Add format-specific options
            if output_format == 'JPEG':
                save_kwargs['quality'] = getattr(settings, 'IMAGE_QUALITY', 95)
                save_kwargs['progressive'] = True
            elif output_format == 'PNG':
                save_kwargs['compress_level'] = 6
            elif output_format == 'WEBP':
                save_kwargs['quality'] = getattr(settings, 'IMAGE_QUALITY', 95)
                save_kwargs['method'] = 6
            
            img.save(output_io, **save_kwargs)
            
            # Create new file
            processed_file = ContentFile(output_io.getvalue())
            processed_file.name = getattr(image_file, 'name', f'processed.{output_format.lower()}')
            
            file_size = len(output_io.getvalue())
            logger.info(f"Image processed successfully: {img.size}, {file_size} bytes, format: {output_format}")
            
            return processed_file, None
            
        except Exception as e:
            logger.error(f"Failed to save processed image: {str(e)}")
            return None, f"Failed to save processed image: {str(e)}"
        
    except Exception as e:
        logger.error(f"Unexpected error processing image: {str(e)}", exc_info=True)
        return None, f"Failed to process image: {str(e)}"


def get_image_metadata(image_file: Union[UploadedFile, File]) -> dict:
    """
    Extract metadata from an image file.
    
    Args:
        image_file: Image file to analyze
        
    Returns:
        dict: Dictionary containing image metadata
    """
    metadata = {
        'width': None,
        'height': None,
        'format': None,
        'mode': None,
        'size_bytes': None,
        'has_transparency': False,
        'exif': {}
    }
    
    try:
        if hasattr(image_file, 'seek'):
            image_file.seek(0)
        
        img = Image.open(image_file)
        
        metadata['width'] = img.width
        metadata['height'] = img.height
        metadata['format'] = img.format
        metadata['mode'] = img.mode
        metadata['has_transparency'] = img.mode in ('RGBA', 'LA', 'PA')
        
        # Get file size
        if hasattr(image_file, 'size'):
            metadata['size_bytes'] = image_file.size
        
        # Extract EXIF data if available
        try:
            exif = img.getexif()
            if exif:
                metadata['exif'] = {k: v for k, v in exif.items() if k}
        except:
            pass
        
        if hasattr(image_file, 'seek'):
            image_file.seek(0)
        
        logger.debug(f"Extracted metadata: {metadata}")
        
    except Exception as e:
        logger.error(f"Failed to extract image metadata: {str(e)}")
    
    return metadata