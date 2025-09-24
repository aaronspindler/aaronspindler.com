"""
Test-specific storage backends for LocalStack S3 mocking.

These backends extend the production storage backends but add
LocalStack-specific configuration for testing.
"""

import os
from storages.backends.s3boto3 import S3Boto3Storage


class LocalStackS3Mixin:
    """Mixin to add LocalStack configuration to S3 storage backends."""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Override settings for LocalStack
        if os.environ.get('USE_LOCALSTACK', 'true').lower() == 'true':
            self.endpoint_url = os.environ.get('AWS_S3_ENDPOINT_URL', 'http://localstack:4566')
            self.use_ssl = os.environ.get('AWS_S3_USE_SSL', 'false').lower() == 'true'
            self.verify = False
            self.access_key = 'test'
            self.secret_key = 'test'
            self.region_name = 'us-east-1'
            self.addressing_style = 'path'  # Use path-style addressing for LocalStack
            self.signature_version = 's3v4'
            
            # Disable custom domain for LocalStack
            self.custom_domain = None
            
    def url(self, name):
        """Override URL generation for LocalStack."""
        if os.environ.get('USE_LOCALSTACK', 'true').lower() == 'true':
            # Generate LocalStack-compatible URLs
            return f"{self.endpoint_url}/{self.bucket_name}/{self.location}/{name}".replace('//', '/')
        return super().url(name)


class TestStaticStorage(LocalStackS3Mixin, S3Boto3Storage):
    """Test storage backend for static files with LocalStack support."""
    location = 'public/static'
    default_acl = 'public-read'
    file_overwrite = True
    querystring_auth = False
    
    def _save(self, name, content):
        """Override _save to handle LocalStack specifics."""
        # Set basic headers for static files
        self.object_parameters = {
            'CacheControl': 'max-age=86400',
            'ACL': 'public-read',
        }
        return super()._save(name, content)


class TestPublicMediaStorage(LocalStackS3Mixin, S3Boto3Storage):
    """Test storage backend for public media files with LocalStack support."""
    location = 'public/media'
    default_acl = 'public-read'
    file_overwrite = True
    querystring_auth = False
    
    def _save(self, name, content):
        """Override _save to handle LocalStack specifics."""
        # Set basic headers for media files
        self.object_parameters = {
            'CacheControl': 'max-age=86400',
            'ACL': 'public-read',
        }
        return super()._save(name, content)


class TestPrivateMediaStorage(LocalStackS3Mixin, S3Boto3Storage):
    """Test storage backend for private media files with LocalStack support."""
    location = 'private/media'
    default_acl = 'private'
    file_overwrite = False
    querystring_auth = True
    querystring_expire = 3600  # URLs expire after 1 hour
    
    def _save(self, name, content):
        """Override _save to handle LocalStack specifics."""
        self.object_parameters = {
            'ACL': 'private',
        }
        return super()._save(name, content)
