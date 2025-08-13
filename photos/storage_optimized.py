"""
Optimized S3 storage backend with CloudFront CDN, multipart uploads, and batch operations.
"""
import os
import logging
import hashlib
import mimetypes
from typing import Optional, Dict, Any, List
from django.conf import settings
from django.core.files.base import ContentFile
from storages.backends.s3boto3 import S3Boto3Storage
import boto3
from boto3.s3.transfer import TransferConfig
from botocore.exceptions import ClientError, NoCredentialsError
from concurrent.futures import ThreadPoolExecutor, as_completed

logger = logging.getLogger(__name__)


class OptimizedS3Storage(S3Boto3Storage):
    """
    Optimized S3 storage with CloudFront CDN and performance improvements.
    """
    
    def __init__(self, *args, **kwargs):
        """
        Initialize optimized S3 storage with custom configuration.
        """
        super().__init__(*args, **kwargs)
        
        # CloudFront configuration
        self.cloudfront_domain = getattr(settings, 'AWS_CLOUDFRONT_DOMAIN', None)
        self.cloudfront_key_id = getattr(settings, 'AWS_CLOUDFRONT_KEY_ID', None)
        self.cloudfront_key = getattr(settings, 'AWS_CLOUDFRONT_KEY', None)
        
        # Transfer configuration for multipart uploads
        self.transfer_config = TransferConfig(
            multipart_threshold=1024 * 25,  # 25MB
            max_concurrency=10,
            multipart_chunksize=1024 * 25,
            use_threads=True,
            max_io_queue=100,
        )
        
        # S3 Transfer Acceleration
        self.use_accelerate = getattr(settings, 'AWS_S3_USE_ACCELERATE', False)
        if self.use_accelerate:
            self.custom_domain = f'{self.bucket_name}.s3-accelerate.amazonaws.com'
        
        # Initialize S3 client with optimized configuration
        self.s3_client = self._get_optimized_s3_client()
    
    def _get_optimized_s3_client(self):
        """
        Get an optimized S3 client with connection pooling.
        
        Returns:
            Boto3 S3 client
        """
        config = boto3.session.Config(
            region_name=self.region_name,
            signature_version='s3v4',
            retries={
                'max_attempts': 3,
                'mode': 'adaptive'
            },
            max_pool_connections=50
        )
        
        if self.use_accelerate:
            config.s3 = {'use_accelerate_endpoint': True}
        
        return boto3.client(
            's3',
            aws_access_key_id=self.access_key,
            aws_secret_access_key=self.secret_key,
            config=config
        )
    
    def url(self, name: str, parameters: Optional[Dict] = None, 
            expire: Optional[int] = None, http_method: Optional[str] = None) -> str:
        """
        Return URL for the file, preferring CloudFront over S3.
        
        Args:
            name: File name/path
            parameters: Additional parameters for the URL
            expire: Expiration time in seconds
            http_method: HTTP method for the URL
            
        Returns:
            URL string
        """
        # Use CloudFront URL if configured
        if self.cloudfront_domain:
            if expire:
                # Generate signed CloudFront URL for private content
                return self._get_cloudfront_signed_url(name, expire)
            else:
                # Use simple CloudFront URL for public content
                return f'https://{self.cloudfront_domain}/{name}'
        
        # Fallback to S3 URL
        return super().url(name, parameters, expire, http_method)
    
    def _get_cloudfront_signed_url(self, name: str, expire: int) -> str:
        """
        Generate a signed CloudFront URL.
        
        Args:
            name: File path
            expire: Expiration time in seconds
            
        Returns:
            Signed CloudFront URL
        """
        from datetime import datetime, timedelta
        from cryptography.hazmat.primitives import hashes
        from cryptography.hazmat.primitives.asymmetric import padding
        from cryptography.hazmat.primitives.serialization import load_pem_private_key
        import base64
        
        url = f'https://{self.cloudfront_domain}/{name}'
        expire_date = datetime.utcnow() + timedelta(seconds=expire)
        
        # Create the policy
        policy = {
            'Statement': [{
                'Resource': url,
                'Condition': {
                    'DateLessThan': {
                        'AWS:EpochTime': int(expire_date.timestamp())
                    }
                }
            }]
        }
        
        # Sign the policy
        if self.cloudfront_key and self.cloudfront_key_id:
            private_key = load_pem_private_key(
                self.cloudfront_key.encode(), 
                password=None
            )
            
            policy_str = json.dumps(policy, separators=(',', ':'))
            signature = private_key.sign(
                policy_str.encode(),
                padding.PKCS1v15(),
                hashes.SHA1()
            )
            
            # Create the signed URL
            params = {
                'Policy': base64.b64encode(policy_str.encode()).decode(),
                'Signature': base64.b64encode(signature).decode(),
                'Key-Pair-Id': self.cloudfront_key_id
            }
            
            query_string = '&'.join([f'{k}={v}' for k, v in params.items()])
            return f'{url}?{query_string}'
        
        return url
    
    def save(self, name: str, content: ContentFile, max_length: Optional[int] = None) -> str:
        """
        Save file with multipart upload for large files.
        
        Args:
            name: File name
            content: File content
            max_length: Maximum length
            
        Returns:
            Saved file name
        """
        # Add cache headers
        self.object_parameters = self.object_parameters or {}
        self.object_parameters.update({
            'CacheControl': 'public, max-age=31536000, immutable',  # 1 year for images
            'ContentType': mimetypes.guess_type(name)[0] or 'application/octet-stream',
        })
        
        # Use multipart upload for large files
        if hasattr(content, 'size') and content.size > 1024 * 1024 * 25:  # 25MB
            logger.info(f"Using multipart upload for {name} ({content.size} bytes)")
            return self._multipart_upload(name, content)
        
        return super().save(name, content, max_length)
    
    def _multipart_upload(self, name: str, content: ContentFile) -> str:
        """
        Perform multipart upload for large files.
        
        Args:
            name: File name
            content: File content
            
        Returns:
            Uploaded file name
        """
        try:
            # Ensure we have the full name with bucket prefix
            name = self._normalize_name(self._clean_name(name))
            
            # Upload with transfer config
            self.s3_client.upload_fileobj(
                content,
                self.bucket_name,
                name,
                ExtraArgs=self.object_parameters,
                Config=self.transfer_config
            )
            
            logger.info(f"Successfully uploaded {name} using multipart upload")
            return name
            
        except Exception as e:
            logger.error(f"Multipart upload failed for {name}: {str(e)}")
            raise
    
    def delete_batch(self, names: List[str]) -> Dict[str, bool]:
        """
        Delete multiple files in a single batch operation.
        
        Args:
            names: List of file names to delete
            
        Returns:
            Dictionary of name -> success status
        """
        results = {}
        
        if not names:
            return results
        
        # Prepare objects for batch delete
        objects = [{'Key': self._normalize_name(self._clean_name(name))} 
                  for name in names]
        
        # Split into chunks (S3 allows max 1000 objects per request)
        chunk_size = 1000
        for i in range(0, len(objects), chunk_size):
            chunk = objects[i:i + chunk_size]
            
            try:
                response = self.s3_client.delete_objects(
                    Bucket=self.bucket_name,
                    Delete={'Objects': chunk}
                )
                
                # Process successful deletions
                for deleted in response.get('Deleted', []):
                    results[deleted['Key']] = True
                
                # Process errors
                for error in response.get('Errors', []):
                    results[error['Key']] = False
                    logger.error(f"Failed to delete {error['Key']}: {error['Message']}")
                    
            except Exception as e:
                logger.error(f"Batch delete failed: {str(e)}")
                for obj in chunk:
                    results[obj['Key']] = False
        
        logger.info(f"Batch deleted {sum(results.values())} of {len(names)} files")
        return results
    
    def copy_batch(self, operations: List[Dict[str, str]]) -> Dict[str, bool]:
        """
        Copy multiple files in parallel.
        
        Args:
            operations: List of {'source': 'path', 'destination': 'path'} dictionaries
            
        Returns:
            Dictionary of destination -> success status
        """
        results = {}
        
        def copy_single(op: Dict[str, str]) -> Tuple[str, bool]:
            """Copy a single file."""
            try:
                source = self._normalize_name(self._clean_name(op['source']))
                dest = self._normalize_name(self._clean_name(op['destination']))
                
                self.s3_client.copy_object(
                    CopySource={'Bucket': self.bucket_name, 'Key': source},
                    Bucket=self.bucket_name,
                    Key=dest,
                    MetadataDirective='COPY'
                )
                
                return dest, True
                
            except Exception as e:
                logger.error(f"Failed to copy {op['source']} to {op['destination']}: {str(e)}")
                return op['destination'], False
        
        # Parallel execution
        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(copy_single, op) for op in operations]
            
            for future in as_completed(futures):
                dest, success = future.result()
                results[dest] = success
        
        logger.info(f"Batch copied {sum(results.values())} of {len(operations)} files")
        return results
    
    def generate_presigned_post(self, key: str, expires_in: int = 3600,
                               conditions: Optional[List] = None) -> Dict[str, Any]:
        """
        Generate presigned POST data for direct browser uploads.
        
        Args:
            key: S3 object key
            expires_in: URL expiration time in seconds
            conditions: List of conditions for the upload
            
        Returns:
            Dictionary with URL and form fields
        """
        conditions = conditions or []
        conditions.extend([
            ['content-length-range', 0, 100 * 1024 * 1024],  # Max 100MB
            ['starts-with', '$Content-Type', 'image/'],
        ])
        
        try:
            response = self.s3_client.generate_presigned_post(
                Bucket=self.bucket_name,
                Key=key,
                ExpiresIn=expires_in,
                Conditions=conditions
            )
            
            logger.debug(f"Generated presigned POST for {key}")
            return response
            
        except Exception as e:
            logger.error(f"Failed to generate presigned POST: {str(e)}")
            raise
    
    def set_object_lifecycle(self, prefix: str, days: int = 90,
                           storage_class: str = 'GLACIER'):
        """
        Set lifecycle policy for objects with specific prefix.
        
        Args:
            prefix: Object key prefix
            days: Days before transition
            storage_class: Target storage class
        """
        lifecycle_config = {
            'Rules': [{
                'ID': f'archive-{prefix}',
                'Status': 'Enabled',
                'Prefix': prefix,
                'Transitions': [{
                    'Days': days,
                    'StorageClass': storage_class
                }],
                'Expiration': {
                    'Days': days * 4  # Expire after 4x transition time
                }
            }]
        }
        
        try:
            self.s3_client.put_bucket_lifecycle_configuration(
                Bucket=self.bucket_name,
                LifecycleConfiguration=lifecycle_config
            )
            
            logger.info(f"Set lifecycle policy for {prefix}: transition to {storage_class} after {days} days")
            
        except Exception as e:
            logger.error(f"Failed to set lifecycle policy: {str(e)}")
            raise
    
    def get_object_metadata(self, name: str) -> Optional[Dict[str, Any]]:
        """
        Get metadata for an S3 object.
        
        Args:
            name: Object key
            
        Returns:
            Metadata dictionary or None
        """
        try:
            key = self._normalize_name(self._clean_name(name))
            response = self.s3_client.head_object(
                Bucket=self.bucket_name,
                Key=key
            )
            
            return {
                'size': response.get('ContentLength'),
                'last_modified': response.get('LastModified'),
                'etag': response.get('ETag'),
                'content_type': response.get('ContentType'),
                'metadata': response.get('Metadata', {}),
                'storage_class': response.get('StorageClass', 'STANDARD'),
            }
            
        except ClientError as e:
            if e.response['Error']['Code'] == '404':
                logger.debug(f"Object {name} not found")
            else:
                logger.error(f"Error getting metadata for {name}: {str(e)}")
            return None
    
    def optimize_storage_class(self, name: str, access_pattern: str = 'infrequent'):
        """
        Optimize storage class based on access pattern.
        
        Args:
            name: Object key
            access_pattern: Access pattern ('frequent', 'infrequent', 'archive')
        """
        storage_class_map = {
            'frequent': 'STANDARD',
            'infrequent': 'STANDARD_IA',
            'archive': 'GLACIER',
            'deep_archive': 'DEEP_ARCHIVE'
        }
        
        storage_class = storage_class_map.get(access_pattern, 'STANDARD_IA')
        key = self._normalize_name(self._clean_name(name))
        
        try:
            # Copy object with new storage class
            self.s3_client.copy_object(
                CopySource={'Bucket': self.bucket_name, 'Key': key},
                Bucket=self.bucket_name,
                Key=key,
                StorageClass=storage_class,
                MetadataDirective='COPY'
            )
            
            logger.info(f"Changed storage class for {name} to {storage_class}")
            
        except Exception as e:
            logger.error(f"Failed to optimize storage class for {name}: {str(e)}")


# Create specialized storage classes
class ThumbnailStorage(OptimizedS3Storage):
    """Storage for thumbnails with aggressive caching."""
    location = 'thumbnails'
    object_parameters = {
        'CacheControl': 'public, max-age=31536000, immutable',
        'ContentDisposition': 'inline',
    }


class OriginalImageStorage(OptimizedS3Storage):
    """Storage for original images with moderate caching."""
    location = 'originals'
    object_parameters = {
        'CacheControl': 'public, max-age=86400',
        'ContentDisposition': 'inline',
    }


class ResponsiveImageStorage(OptimizedS3Storage):
    """Storage for responsive images with CDN optimization."""
    location = 'responsive'
    object_parameters = {
        'CacheControl': 'public, max-age=31536000, immutable',
        'ContentDisposition': 'inline',
    }