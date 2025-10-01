"""
Management command to backfill RequestFingerprint records from PageVisit data.
"""
import hashlib
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from pages.models import PageVisit
from utils.models.security import RequestFingerprint


class Command(BaseCommand):
    help = 'Backfill RequestFingerprint records from existing PageVisit records'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be created without actually creating records',
        )
        parser.add_argument(
            '--batch-size',
            type=int,
            default=1000,
            help='Number of records to create per batch (default: 1000)',
        )

    def generate_fingerprint(self, ip_address, method, path, user_agent, include_ip=True):
        """
        Generate a SHA256 fingerprint from request data.
        
        Args:
            ip_address: IP address string
            method: HTTP method
            path: Request path
            user_agent: User agent string
            include_ip: Whether to include IP in fingerprint
            
        Returns:
            str: SHA256 hash as hex string
        """
        components = []
        if include_ip:
            components.append(str(ip_address))
        components.extend([method, path, user_agent])
        
        data = '|'.join(components)
        return hashlib.sha256(data.encode('utf-8')).hexdigest()

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        batch_size = options['batch_size']
        
        if dry_run:
            self.stdout.write(self.style.WARNING('DRY RUN MODE - No records will be created'))
        
        # Get all PageVisit records
        page_visits = PageVisit.objects.all()
        total_visits = page_visits.count()
        
        if total_visits == 0:
            self.stdout.write(self.style.WARNING('No PageVisit records found to backfill'))
            return
        
        self.stdout.write(f'Found {total_visits} PageVisit records to process')
        
        # Check for existing RequestFingerprint records
        existing_count = RequestFingerprint.objects.count()
        self.stdout.write(f'Current RequestFingerprint count: {existing_count}')
        
        # Process records
        fingerprints_to_create = []
        processed = 0
        created = 0
        
        for visit in page_visits.iterator(chunk_size=batch_size):
            processed += 1
            
            # Use page_name as path (e.g., "home" -> "/home")
            path = visit.page_name if visit.page_name.startswith('/') else f'/{visit.page_name}'
            
            # Default values for missing data
            method = 'GET'  # Most page visits are GET requests
            user_agent = ''  # No user agent data in PageVisit
            is_secure = True  # Assume HTTPS
            is_ajax = False  # Regular page visits are not AJAX
            
            # Generate fingerprints
            fingerprint = self.generate_fingerprint(visit.ip_address, method, path, user_agent, include_ip=True)
            fingerprint_no_ip = self.generate_fingerprint(visit.ip_address, method, path, user_agent, include_ip=False)
            
            # Create RequestFingerprint instance
            rf = RequestFingerprint(
                created_at=visit.created_at,
                fingerprint=fingerprint,
                fingerprint_no_ip=fingerprint_no_ip,
                ip_address=visit.ip_address,
                method=method,
                path=path,
                is_secure=is_secure,
                is_ajax=is_ajax,
                user_agent=user_agent,
                browser='',
                browser_version='',
                os='',
                device='',
                headers={},
                is_suspicious=False,
                suspicious_reason='',
                user=None,
            )
            
            if dry_run:
                # Show sample of what would be created
                if processed <= 5:
                    self.stdout.write(
                        f'  Would create: {rf.ip_address} | {rf.method} {rf.path} | {rf.created_at}'
                    )
            else:
                fingerprints_to_create.append(rf)
            
            # Batch create when we hit the batch size
            if not dry_run and len(fingerprints_to_create) >= batch_size:
                with transaction.atomic():
                    RequestFingerprint.objects.bulk_create(fingerprints_to_create, batch_size=batch_size)
                created += len(fingerprints_to_create)
                self.stdout.write(f'Created {created}/{total_visits} records...')
                fingerprints_to_create = []
        
        # Create any remaining records
        if not dry_run and fingerprints_to_create:
            with transaction.atomic():
                RequestFingerprint.objects.bulk_create(fingerprints_to_create, batch_size=batch_size)
            created += len(fingerprints_to_create)
        
        # Final summary
        if dry_run:
            self.stdout.write(
                self.style.WARNING(f'\nDRY RUN COMPLETE: Would create {total_visits} RequestFingerprint records')
            )
            if processed > 5:
                self.stdout.write('  (showing first 5 samples above)')
        else:
            self.stdout.write(
                self.style.SUCCESS(f'\nSuccessfully created {created} RequestFingerprint records')
            )
            new_total = RequestFingerprint.objects.count()
            self.stdout.write(f'New RequestFingerprint count: {new_total}')

