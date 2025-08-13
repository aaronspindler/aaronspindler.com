"""
Custom storage backend for AWS S3 with enhanced error handling and logging.
"""
import logging
from typing import Optional, Any, Dict, Tuple
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.core.files.base import File
from storages.backends.s3boto3 import S3Boto3Storage
from botocore.exceptions import ClientError, NoCredentialsError, BotoCoreError

# Set up logger
logger = logging.getLogger(__name__)


class MediaStorage(S3Boto3Storage):
    """
    Custom S3 storage class for media files with enhanced error handling and logging.
    
    Extends S3Boto3Storage to provide specific configuration for our media files
    with comprehensive error handling and retry logic.
    
    Attributes:
        bucket_name: The S3 bucket name for storing media files
        custom_domain: Custom domain for serving files (e.g., CloudFront)
        file_overwrite: Whether to overwrite existing files
        default_acl: Default ACL for uploaded files
        location: Prefix path within the bucket
    """
    
    bucket_name: Optional[str] = None
    custom_domain: Optional[str] = None
    file_overwrite: bool = False
    default_acl: str = 'public-read'
    location: str = ''  # Root of the bucket
    max_retries: int = 3  # Maximum number of retries for S3 operations
    
    def __init__(self, *args, **kwargs) -> None:
        """
        Initialize the storage backend with AWS credentials and error handling.
        
        Args:
            *args: Variable length argument list
            **kwargs: Arbitrary keyword arguments
            
        Raises:
            ImproperlyConfigured: If required AWS settings are missing
        """
        try:
            # Validate required settings
            self._validate_settings()
            
            # Set bucket and domain from settings
            self.bucket_name = getattr(settings, 'AWS_STORAGE_BUCKET_NAME', None)
            self.custom_domain = getattr(settings, 'AWS_S3_CUSTOM_DOMAIN', None)
            
            # Initialize parent class
            super().__init__(*args, **kwargs)
            
            # Store credentials for reference
            self.access_key = settings.AWS_ACCESS_KEY_ID
            self.secret_key = settings.AWS_SECRET_ACCESS_KEY
            self.region_name = settings.AWS_S3_REGION_NAME
            
            logger.info(f"MediaStorage initialized with bucket: {self.bucket_name}")
            
        except ImproperlyConfigured as e:
            logger.error(f"Storage configuration error: {str(e)}")
            raise
            
        except Exception as e:
            logger.error(f"Unexpected error initializing storage: {str(e)}", exc_info=True)
            raise ImproperlyConfigured(f"Failed to initialize storage backend: {str(e)}")
    
    def _validate_settings(self) -> None:
        """
        Validate that all required AWS settings are present.
        
        Raises:
            ImproperlyConfigured: If any required setting is missing
        """
        required_settings = [
            ('AWS_ACCESS_KEY_ID', 'AWS Access Key ID'),
            ('AWS_SECRET_ACCESS_KEY', 'AWS Secret Access Key'),
            ('AWS_STORAGE_BUCKET_NAME', 'AWS S3 Bucket Name'),
            ('AWS_S3_REGION_NAME', 'AWS S3 Region Name'),
        ]
        
        missing_settings = []
        for setting_name, description in required_settings:
            if not getattr(settings, setting_name, None):
                missing_settings.append(description)
        
        if missing_settings:
            error_msg = f"Missing required AWS settings: {', '.join(missing_settings)}"
            logger.error(error_msg)
            raise ImproperlyConfigured(error_msg)
    
    def _save(self, name: str, content: File) -> str:
        """
        Save the file to S3 with retry logic and error handling.
        
        Args:
            name: The name/path for the file
            content: The file content to save
            
        Returns:
            str: The actual name of the saved file
            
        Raises:
            Exception: If file cannot be saved after retries
        """
        retry_count = 0
        last_error = None
        
        while retry_count < self.max_retries:
            try:
                logger.debug(f"Attempting to save file: {name} (attempt {retry_count + 1})")
                
                # Call parent save method
                saved_name = super()._save(name, content)
                
                logger.info(f"Successfully saved file to S3: {saved_name}")
                return saved_name
                
            except NoCredentialsError as e:
                logger.error(f"AWS credentials not found: {str(e)}")
                raise  # Don't retry credential errors
                
            except ClientError as e:
                error_code = e.response.get('Error', {}).get('Code', 'Unknown')
                error_message = e.response.get('Error', {}).get('Message', str(e))
                
                if error_code == 'NoSuchBucket':
                    logger.error(f"S3 bucket does not exist: {self.bucket_name}")
                    raise  # Don't retry if bucket doesn't exist
                    
                elif error_code == 'AccessDenied':
                    logger.error(f"Access denied to S3 bucket: {error_message}")
                    raise  # Don't retry permission errors
                    
                else:
                    logger.warning(f"S3 client error (attempt {retry_count + 1}): {error_message}")
                    last_error = e
                    retry_count += 1
                    
            except BotoCoreError as e:
                logger.warning(f"S3 connection error (attempt {retry_count + 1}): {str(e)}")
                last_error = e
                retry_count += 1
                
            except Exception as e:
                logger.error(f"Unexpected error saving to S3: {str(e)}", exc_info=True)
                last_error = e
                retry_count += 1
        
        # If we've exhausted retries, raise the last error
        error_msg = f"Failed to save file {name} after {self.max_retries} attempts"
        logger.error(f"{error_msg}. Last error: {str(last_error)}")
        raise Exception(error_msg) from last_error
    
    def delete(self, name: str) -> None:
        """
        Delete a file from S3 with error handling.
        
        Args:
            name: The name/path of the file to delete
            
        Returns:
            None
        """
        try:
            logger.debug(f"Attempting to delete file from S3: {name}")
            
            super().delete(name)
            
            logger.info(f"Successfully deleted file from S3: {name}")
            
        except ClientError as e:
            error_code = e.response.get('Error', {}).get('Code', 'Unknown')
            error_message = e.response.get('Error', {}).get('Message', str(e))
            
            if error_code == 'NoSuchKey':
                logger.warning(f"File not found in S3, ignoring deletion: {name}")
                # Don't raise error if file doesn't exist
                
            else:
                logger.error(f"Error deleting file from S3: {error_message}")
                raise
                
        except Exception as e:
            logger.error(f"Unexpected error deleting from S3: {str(e)}", exc_info=True)
            raise
    
    def exists(self, name: str) -> bool:
        """
        Check if a file exists in S3 with error handling.
        
        Args:
            name: The name/path of the file to check
            
        Returns:
            bool: True if file exists, False otherwise
        """
        try:
            logger.debug(f"Checking if file exists in S3: {name}")
            
            exists = super().exists(name)
            
            logger.debug(f"File {'exists' if exists else 'does not exist'}: {name}")
            return exists
            
        except ClientError as e:
            error_code = e.response.get('Error', {}).get('Code', 'Unknown')
            
            if error_code in ['NoSuchBucket', 'AccessDenied']:
                logger.error(f"Cannot check file existence: {e.response.get('Error', {}).get('Message', str(e))}")
                return False
                
            logger.warning(f"Error checking file existence: {str(e)}")
            return False
            
        except Exception as e:
            logger.error(f"Unexpected error checking file existence: {str(e)}", exc_info=True)
            return False
    
    def size(self, name: str) -> int:
        """
        Get the size of a file in S3 with error handling.
        
        Args:
            name: The name/path of the file
            
        Returns:
            int: Size of the file in bytes, or 0 if error occurs
        """
        try:
            logger.debug(f"Getting size of file in S3: {name}")
            
            file_size = super().size(name)
            
            logger.debug(f"File size for {name}: {file_size} bytes")
            return file_size
            
        except ClientError as e:
            error_message = e.response.get('Error', {}).get('Message', str(e))
            logger.error(f"Error getting file size from S3: {error_message}")
            return 0
            
        except Exception as e:
            logger.error(f"Unexpected error getting file size: {str(e)}", exc_info=True)
            return 0
    
    def get_available_name(self, name: str, max_length: Optional[int] = None) -> str:
        """
        Get an available filename that doesn't conflict with existing files.
        
        Since we have file_overwrite = False, this will add a suffix if needed.
        
        Args:
            name: The desired filename
            max_length: Maximum length for the filename
            
        Returns:
            str: An available filename
        """
        try:
            logger.debug(f"Getting available name for: {name}")
            
            available_name = super().get_available_name(name, max_length)
            
            if available_name != name:
                logger.info(f"File name modified to avoid conflict: {name} -> {available_name}")
            
            return available_name
            
        except Exception as e:
            logger.error(f"Error getting available name: {str(e)}", exc_info=True)
            # Return original name as fallback
            return name
    
    def url(self, name: str) -> str:
        """
        Generate the URL for accessing a file with error handling.
        
        Args:
            name: The name/path of the file
            
        Returns:
            str: Public URL for the file
        """
        try:
            if self.custom_domain:
                # Use custom domain (e.g., CloudFront)
                url = f"https://{self.custom_domain}/{name}"
                logger.debug(f"Generated custom domain URL: {url}")
                
            else:
                # Use S3 direct URL
                url = super().url(name)
                logger.debug(f"Generated S3 URL: {url}")
            
            return url
            
        except Exception as e:
            logger.error(f"Error generating URL for {name}: {str(e)}", exc_info=True)
            # Return a fallback URL
            if self.custom_domain:
                return f"https://{self.custom_domain}/{name}"
            return f"https://{self.bucket_name}.s3.amazonaws.com/{name}"
    
    def get_modified_time(self, name: str) -> Optional[Any]:
        """
        Get the last modified time of a file with error handling.
        
        Args:
            name: The name/path of the file
            
        Returns:
            Optional[Any]: Last modified datetime or None if error
        """
        try:
            logger.debug(f"Getting modified time for: {name}")
            
            modified_time = super().get_modified_time(name)
            
            logger.debug(f"Modified time for {name}: {modified_time}")
            return modified_time
            
        except Exception as e:
            logger.error(f"Error getting modified time: {str(e)}", exc_info=True)
            return None
    
    def listdir(self, path: str) -> Tuple[list, list]:
        """
        List the contents of a directory in S3 with error handling.
        
        Args:
            path: The directory path to list
            
        Returns:
            Tuple[list, list]: Tuple of (directories, files)
        """
        try:
            logger.debug(f"Listing directory: {path}")
            
            dirs, files = super().listdir(path)
            
            logger.debug(f"Found {len(dirs)} directories and {len(files)} files in {path}")
            return dirs, files
            
        except ClientError as e:
            error_message = e.response.get('Error', {}).get('Message', str(e))
            logger.error(f"Error listing S3 directory: {error_message}")
            return [], []
            
        except Exception as e:
            logger.error(f"Unexpected error listing directory: {str(e)}", exc_info=True)
            return [], []
    
    def get_accessed_time(self, name: str) -> Optional[Any]:
        """
        Get the last accessed time of a file.
        
        Note: S3 doesn't track access time, so this returns modified time.
        
        Args:
            name: The name/path of the file
            
        Returns:
            Optional[Any]: Last accessed datetime (actually modified time) or None
        """
        logger.debug(f"Getting accessed time for: {name} (using modified time)")
        return self.get_modified_time(name)
    
    def get_created_time(self, name: str) -> Optional[Any]:
        """
        Get the creation time of a file.
        
        Args:
            name: The name/path of the file
            
        Returns:
            Optional[Any]: Creation datetime or None if error
        """
        try:
            logger.debug(f"Getting created time for: {name}")
            
            created_time = super().get_created_time(name)
            
            logger.debug(f"Created time for {name}: {created_time}")
            return created_time
            
        except Exception as e:
            logger.error(f"Error getting created time: {str(e)}", exc_info=True)
            return None


def test_s3_connection() -> Dict[str, Any]:
    """
    Test the S3 connection and permissions.
    
    Returns:
        Dict[str, Any]: Dictionary with test results
    """
    results = {
        'connection': False,
        'bucket_exists': False,
        'can_write': False,
        'can_read': False,
        'can_delete': False,
        'errors': []
    }
    
    try:
        storage = MediaStorage()
        results['connection'] = True
        
        # Test bucket existence
        try:
            storage.exists('test-connection.txt')
            results['bucket_exists'] = True
        except Exception as e:
            results['errors'].append(f"Bucket check failed: {str(e)}")
        
        # Test write permission
        try:
            from django.core.files.base import ContentFile
            test_file = ContentFile(b"test content")
            test_name = storage.save('test-connection.txt', test_file)
            results['can_write'] = True
            
            # Test read permission
            try:
                storage.size(test_name)
                results['can_read'] = True
            except Exception as e:
                results['errors'].append(f"Read test failed: {str(e)}")
            
            # Test delete permission
            try:
                storage.delete(test_name)
                results['can_delete'] = True
            except Exception as e:
                results['errors'].append(f"Delete test failed: {str(e)}")
                
        except Exception as e:
            results['errors'].append(f"Write test failed: {str(e)}")
        
    except Exception as e:
        results['errors'].append(f"Connection failed: {str(e)}")
    
    logger.info(f"S3 connection test results: {results}")
    return results