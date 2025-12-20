import mimetypes

from storages.backends.s3boto3 import S3Boto3Storage


class PublicMediaStorage(S3Boto3Storage):
    """Storage backend for public media files (like photos)"""

    location = "public/media"
    default_acl = "public-read"
    file_overwrite = True
    querystring_auth = False

    def _save(self, name, content):
        """
        Override _save to set proper content type and caching headers for images.
        """
        # Determine content type
        content_type, _ = mimetypes.guess_type(name)
        if content_type:
            content.content_type = content_type

        # Set cache control for images (1 year for optimized images)
        if any(size in name for size in ["optimized", "thumbnail", "preview"]):
            # Optimized versions can be cached longer
            self.object_parameters = {
                "CacheControl": "public, max-age=31536000",  # 1 year
                "ContentType": content_type or "application/octet-stream",
            }
        else:
            # Original images get standard cache
            self.object_parameters = {
                "CacheControl": "public, max-age=86400",  # 1 day
                "ContentType": content_type or "application/octet-stream",
            }

        return super()._save(name, content)


class PrivateMediaStorage(S3Boto3Storage):
    """Storage backend for private media files (if needed in the future)"""

    location = "private/media"
    default_acl = "private"
    file_overwrite = False
    querystring_auth = True  # Add authentication to URLs for private files
    querystring_expire = 3600  # URLs expire after 1 hour
