"""
Management command to clean up orphaned S3 objects.
"""
import logging
from datetime import datetime, timedelta
from django.core.management.base import BaseCommand, CommandError
from django.conf import settings
from photos.models import Photo
from photos.storage_optimized import OptimizedS3Storage
import boto3
from botocore.exceptions import ClientError

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Clean up orphaned S3 objects that are no longer referenced in the database'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be deleted without actually deleting'
        )
        parser.add_argument(
            '--older-than-days',
            type=int,
            default=7,
            help='Only delete objects older than this many days'
        )
        parser.add_argument(
            '--prefix',
            type=str,
            default='albums/',
            help='S3 prefix to scan'
        )
        parser.add_argument(
            '--batch-size',
            type=int,
            default=100,
            help='Number of objects to process at once'
        )
        parser.add_argument(
            '--include-thumbnails',
            action='store_true',
            help='Also check and clean thumbnail objects'
        )
        parser.add_argument(
            '--archive-instead',
            action='store_true',
            help='Move to Glacier instead of deleting'
        )
    
    def handle(self, *args, **options):
        dry_run = options.get('dry_run')
        older_than_days = options.get('older_than_days')
        prefix = options.get('prefix')
        batch_size = options.get('batch_size')
        include_thumbnails = options.get('include_thumbnails')
        archive_instead = options.get('archive_instead')
        
        if dry_run:
            self.stdout.write(self.style.WARNING('DRY RUN MODE - No files will be deleted'))
        
        try:
            orphaned = self._find_orphaned_objects(prefix, older_than_days, include_thumbnails)
            
            if not orphaned:
                self.stdout.write(self.style.SUCCESS('No orphaned objects found'))
                return
            
            self.stdout.write(f'Found {len(orphaned)} orphaned objects')
            
            # Calculate total size
            total_size = sum(obj.get('Size', 0) for obj in orphaned)
            self.stdout.write(f'Total size: {self._format_size(total_size)}')
            
            if dry_run:
                self._show_dry_run_results(orphaned)
            else:
                if archive_instead:
                    self._archive_objects(orphaned, batch_size)
                else:
                    self._delete_objects(orphaned, batch_size)
                    
        except Exception as e:
            logger.error(f"S3 cleanup failed: {str(e)}")
            raise CommandError(f"S3 cleanup failed: {str(e)}")
    
    def _find_orphaned_objects(self, prefix, older_than_days, include_thumbnails):
        """Find S3 objects that are not referenced in the database."""
        storage = OptimizedS3Storage()
        s3_client = storage.s3_client
        
        # Get all S3 objects
        s3_objects = []
        paginator = s3_client.get_paginator('list_objects_v2')
        
        self.stdout.write(f'Scanning S3 bucket for objects with prefix: {prefix}')
        
        cutoff_date = datetime.now() - timedelta(days=older_than_days)
        
        for page in paginator.paginate(Bucket=storage.bucket_name, Prefix=prefix):
            if 'Contents' in page:
                for obj in page['Contents']:
                    # Check age
                    if obj['LastModified'].replace(tzinfo=None) < cutoff_date:
                        s3_objects.append(obj)
        
        self.stdout.write(f'Found {len(s3_objects)} S3 objects older than {older_than_days} days')
        
        # Get all database references
        db_original_images = set(
            Photo.objects.exclude(original_image='').values_list('original_image', flat=True)
        )
        
        if include_thumbnails:
            db_thumbnails = set(
                Photo.objects.exclude(thumbnail='').values_list('thumbnail', flat=True)
            )
            db_references = db_original_images | db_thumbnails
        else:
            db_references = db_original_images
        
        self.stdout.write(f'Found {len(db_references)} database references')
        
        # Find orphaned objects
        orphaned = []
        for obj in s3_objects:
            key = obj['Key']
            
            # Check if the key is referenced in database
            if not any(ref in key for ref in db_references):
                orphaned.append(obj)
        
        return orphaned
    
    def _show_dry_run_results(self, orphaned):
        """Show what would be deleted in dry run mode."""
        self.stdout.write('\nOrphaned objects that would be deleted:')
        self.stdout.write('='*60)
        
        # Group by directory
        by_directory = {}
        for obj in orphaned:
            directory = '/'.join(obj['Key'].split('/')[:-1])
            if directory not in by_directory:
                by_directory[directory] = []
            by_directory[directory].append(obj)
        
        for directory, objects in sorted(by_directory.items()):
            self.stdout.write(f'\n{directory}/ ({len(objects)} files):')
            for obj in objects[:5]:  # Show first 5 files
                self.stdout.write(
                    f"  - {obj['Key'].split('/')[-1]} "
                    f"({self._format_size(obj.get('Size', 0))}, "
                    f"modified: {obj['LastModified'].strftime('%Y-%m-%d')})"
                )
            if len(objects) > 5:
                self.stdout.write(f'  ... and {len(objects) - 5} more')
    
    def _delete_objects(self, objects, batch_size):
        """Delete orphaned objects from S3."""
        storage = OptimizedS3Storage()
        
        total = len(objects)
        deleted = 0
        failed = 0
        
        self.stdout.write(f'\nDeleting {total} orphaned objects...')
        
        # Process in batches
        for i in range(0, total, batch_size):
            batch = objects[i:i + batch_size]
            keys = [obj['Key'] for obj in batch]
            
            results = storage.delete_batch(keys)
            
            batch_deleted = sum(1 for success in results.values() if success)
            batch_failed = len(results) - batch_deleted
            
            deleted += batch_deleted
            failed += batch_failed
            
            self.stdout.write(f'Progress: {deleted + failed}/{total} processed')
        
        # Summary
        self.stdout.write(
            self.style.SUCCESS(
                f'\nCleanup complete: {deleted} deleted, {failed} failed'
            )
        )
        
        if deleted > 0:
            freed_space = sum(obj.get('Size', 0) for obj in objects[:deleted])
            self.stdout.write(f'Freed space: {self._format_size(freed_space)}')
    
    def _archive_objects(self, objects, batch_size):
        """Archive objects to Glacier instead of deleting."""
        storage = OptimizedS3Storage()
        s3_client = storage.s3_client
        
        total = len(objects)
        archived = 0
        failed = 0
        
        self.stdout.write(f'\nArchiving {total} orphaned objects to Glacier...')
        
        for obj in objects:
            try:
                # Change storage class to Glacier
                s3_client.copy_object(
                    CopySource={'Bucket': storage.bucket_name, 'Key': obj['Key']},
                    Bucket=storage.bucket_name,
                    Key=obj['Key'],
                    StorageClass='GLACIER',
                    MetadataDirective='COPY'
                )
                archived += 1
                
                if archived % 10 == 0:
                    self.stdout.write(f'Progress: {archived}/{total} archived')
                    
            except Exception as e:
                failed += 1
                logger.error(f"Failed to archive {obj['Key']}: {str(e)}")
        
        self.stdout.write(
            self.style.SUCCESS(
                f'\nArchiving complete: {archived} archived, {failed} failed'
            )
        )
    
    def _format_size(self, size_bytes):
        """Format size in human-readable format."""
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if size_bytes < 1024.0:
                return f"{size_bytes:.2f} {unit}"
            size_bytes /= 1024.0
        return f"{size_bytes:.2f} PB"