"""
Management command to remove local/private IP request fingerprints.

This command identifies and removes RequestFingerprint records with local or private
IP addresses (localhost, 10.x.x.x, 192.168.x.x, 172.16-31.x.x).

Since the middleware now skips tracking local requests, this command helps clean up
any historical local request data that was collected before the filtering was implemented.

Usage:
    python manage.py remove_local_fingerprints
    python manage.py remove_local_fingerprints --dry-run  # Preview without deleting
    python manage.py remove_local_fingerprints --limit 100  # Delete up to 100 records

Features:
    - Identifies all local/private IP addresses using is_local_ip()
    - Shows detailed statistics before deletion
    - Supports dry-run mode to preview before deletion
    - Provides clear progress feedback

Local/Private IP Ranges Detected:
    - Localhost: 127.0.0.1, ::1, localhost
    - Private Class A: 10.0.0.0/8
    - Private Class B: 192.168.0.0/16
    - Private Class C: 172.16.0.0/12

Recommended Usage:
    - Run with --dry-run first to preview
    - Run once after deploying the local IP filtering middleware
    - Can be run periodically to clean up any stray local records

Documentation:
    See CLAUDE.md for complete documentation
"""

from collections import Counter

from django.core.management.base import BaseCommand

from utils.models.security import RequestFingerprint
from utils.security import is_local_ip


class Command(BaseCommand):
    help = "Remove RequestFingerprint records with local/private IP addresses"

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Preview which records would be deleted without actually deleting them",
        )
        parser.add_argument(
            "--limit",
            type=int,
            help="Maximum number of records to delete",
        )

    def handle(self, *args, **options):
        dry_run = options.get("dry_run", False)
        limit = options.get("limit")

        if dry_run:
            self.stdout.write(self.style.WARNING("🔍 DRY RUN MODE - No records will be deleted"))
            self.stdout.write("")

        # Get all distinct IP addresses
        all_ips = RequestFingerprint.objects.values_list("ip_address", flat=True).distinct()

        # Filter for local IPs
        local_ips = [ip for ip in all_ips if is_local_ip(ip)]

        if not local_ips:
            self.stdout.write(self.style.SUCCESS("✅ No local IP fingerprints found"))
            return

        # Get queryset of records to delete
        queryset = RequestFingerprint.objects.filter(ip_address__in=local_ips)
        total_count = queryset.count()

        if limit:
            queryset = queryset[:limit]
            delete_count = min(total_count, limit)
        else:
            delete_count = total_count

        # Show statistics
        self.stdout.write(f"📊 Found {len(local_ips)} unique local/private IP addresses")
        self.stdout.write(f"📝 Total local fingerprint records: {total_count}")

        # Show IP breakdown
        ip_counter = Counter(
            RequestFingerprint.objects.filter(ip_address__in=local_ips).values_list("ip_address", flat=True)
        )

        self.stdout.write("")
        self.stdout.write("🔍 Top local IPs:")
        for ip, count in ip_counter.most_common(10):
            self.stdout.write(f"  • {ip}: {count} records")

        if len(ip_counter) > 10:
            self.stdout.write(f"  ... and {len(ip_counter) - 10} more")

        self.stdout.write("")

        if dry_run:
            self.stdout.write(
                self.style.WARNING(
                    f"💡 Would delete {delete_count} record(s) "
                    f"{'(limited)' if limit and limit < total_count else ''}"
                )
            )
            self.stdout.write("")
            self.stdout.write(self.style.SUCCESS("🔍 Dry run complete - no changes made"))
            return

        # Confirm deletion
        self.stdout.write(
            self.style.WARNING(
                f"⚠️  About to delete {delete_count} local fingerprint record(s) "
                f"{'(limited)' if limit and limit < total_count else ''}"
            )
        )

        # Delete records
        deleted_count, _ = queryset.delete()

        self.stdout.write("")
        self.stdout.write(self.style.SUCCESS(f"✅ Successfully deleted {deleted_count} local fingerprint records"))

        if limit and total_count > limit:
            remaining = total_count - deleted_count
            self.stdout.write(
                self.style.WARNING(
                    f"ℹ️  {remaining} local fingerprint records remaining (use --limit or run again to delete more)"
                )
            )
