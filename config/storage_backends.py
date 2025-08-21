from django.conf import settings
from storages.backends.s3boto3 import S3Boto3Storage
from django.core.files.base import File
import mimetypes


class StaticStorage(S3Boto3Storage):
    """Storage backend for static files"""
    location = 'public/static'
    default_acl = 'public-read'
    file_overwrite = False
    querystring_auth = False  # Don't add authentication to URLs for static files


class PublicMediaStorage(S3Boto3Storage):
    """Storage backend for public media files (like photos)"""
    location = 'public/media'
    default_acl = 'public-read'
    file_overwrite = False
    querystring_auth = False  # Don't add authentication to URLs for public media
    
    def _save(self, name, content):
        """
        Override _save to set proper content type and caching headers for images.
        """
        # Determine content type
        content_type, _ = mimetypes.guess_type(name)
        if content_type:
            content.content_type = content_type
        
        # Set cache control for images (1 year for optimized images)
        if any(size in name for size in ['thumbnail', 'small', 'medium', 'large']):
            # Optimized versions can be cached longer
            self.object_parameters = {
                'CacheControl': 'public, max-age=31536000',  # 1 year
                'ContentType': content_type or 'application/octet-stream',
            }
        else:
            # Original images get standard cache
            self.object_parameters = {
                'CacheControl': 'public, max-age=86400',  # 1 day
                'ContentType': content_type or 'application/octet-stream',
            }
        
        return super()._save(name, content)


class OptimizedImageStorage(S3Boto3Storage):
    """
    Specialized storage for optimized images with aggressive caching
    and proper content types.
    """
    location = 'public/media/optimized'
    default_acl = 'public-read'
    file_overwrite = False
    querystring_auth = False
    
    # Set long cache times for optimized images
    object_parameters = {
        'CacheControl': 'public, max-age=31536000, immutable',  # 1 year, immutable
    }
    
    def _save(self, name, content):
        """
        Override _save to ensure proper content type.
        """
        content_type, _ = mimetypes.guess_type(name)
        if content_type:
            self.object_parameters['ContentType'] = content_type
        
        return super()._save(name, content)


class PrivateMediaStorage(S3Boto3Storage):
    """Storage backend for private media files (if needed in the future)"""
    location = 'private/media'
    default_acl = 'private'
    file_overwrite = False
    querystring_auth = True  # Add authentication to URLs for private files
    querystring_expire = 3600  # URLs expire after 1 hour
