"""
Management command to remove local/private IP records and their related fingerprints.

This command identifies and removes IPAddress records (and their related RequestFingerprint
records via cascade delete) with local or private IP addresses (localhost, 10.x.x.x,
192.168.x.x, 172.16-31.x.x).

Since the middleware now skips tracking local requests, this command helps clean up
any historical local request data that was collected before the filtering was implemented.

With the normalized IP structure, each unique IP address is stored once in the IPAddress
model, and all related RequestFingerprint records reference it via ForeignKey. Deleting
an IPAddress record automatically deletes all associated RequestFingerprint records.

Usage:
    python manage.py remove_local_fingerprints
    python manage.py remove_local_fingerprints --dry-run  # Preview without deleting
    python manage.py remove_local_fingerprints --limit 100  # Delete up to 100 IP records

Features:
    - Identifies all local/private IP addresses using is_local_ip()
    - Shows detailed statistics before deletion (IP count + related fingerprint count)
    - Supports dry-run mode to preview before deletion
    - Provides clear progress feedback
    - Cascade deletes related RequestFingerprint records automatically

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

from django.core.management.base import BaseCommand

from utils.models.security import IPAddress, RequestFingerprint
from utils.security import is_local_ip


class Command(BaseCommand):
    help = "Remove IPAddress records (and their related RequestFingerprint records) with local/private IP addresses"

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Preview which records would be deleted without actually deleting them",
        )
        parser.add_argument(
            "--limit",
            type=int,
            help="Maximum number of IPAddress records to delete",
        )

    def handle(self, *args, **options):
        dry_run = options.get("dry_run", False)
        limit = options.get("limit")

        if dry_run:
            self.stdout.write(self.style.WARNING("🔍 DRY RUN MODE - No records will be deleted"))
            self.stdout.write("")

        # Get all IPAddress records
        all_ip_addresses = IPAddress.objects.all()

        # Filter for local IPs
        local_ip_objs = [ip_obj for ip_obj in all_ip_addresses if is_local_ip(ip_obj.ip_address)]

        if not local_ip_objs:
            self.stdout.write(self.style.SUCCESS("✅ No local IP records found"))
            return

        # Get PKs for queryset filtering
        local_ip_pks = [ip_obj.pk for ip_obj in local_ip_objs]

        # Get queryset of IPAddress records to delete
        queryset = IPAddress.objects.filter(pk__in=local_ip_pks)
        total_ip_count = queryset.count()

        # Count related RequestFingerprint records
        total_fingerprint_count = RequestFingerprint.objects.filter(ip_address__pk__in=local_ip_pks).count()

        if limit:
            delete_ip_count = min(total_ip_count, limit)
            # Get limited PKs first (can't delete a sliced queryset)
            limited_pks = list(queryset.values_list("pk", flat=True)[:limit])
            # Filter by limited PKs for deletion
            queryset = IPAddress.objects.filter(pk__in=limited_pks)
            # Count fingerprints for limited set
            delete_fingerprint_count = RequestFingerprint.objects.filter(ip_address__pk__in=limited_pks).count()
        else:
            delete_ip_count = total_ip_count
            delete_fingerprint_count = total_fingerprint_count

        # Show statistics
        self.stdout.write(f"📊 Found {len(local_ip_objs)} unique local/private IP addresses")
        self.stdout.write(f"📝 Total local fingerprint records: {total_fingerprint_count}")

        # Show IP breakdown with request counts
        ip_breakdown = []
        for ip_obj in local_ip_objs:
            fingerprint_count = ip_obj.request_fingerprints.count()
            ip_breakdown.append((ip_obj.ip_address, fingerprint_count))

        # Sort by fingerprint count (descending)
        ip_breakdown.sort(key=lambda x: x[1], reverse=True)

        self.stdout.write("")
        self.stdout.write("🔍 Top local IPs:")
        for ip, count in ip_breakdown[:10]:
            self.stdout.write(f"  • {ip}: {count} fingerprint records")

        if len(ip_breakdown) > 10:
            self.stdout.write(f"  ... and {len(ip_breakdown) - 10} more")

        self.stdout.write("")

        if dry_run:
            self.stdout.write(
                self.style.WARNING(
                    f"💡 Would delete {delete_ip_count} IP record(s) "
                    f"and {delete_fingerprint_count} related fingerprint record(s) "
                    f"{'(limited)' if limit and limit < total_ip_count else ''}"
                )
            )
            self.stdout.write("")
            self.stdout.write(self.style.SUCCESS("🔍 Dry run complete - no changes made"))
            return

        # Confirm deletion
        self.stdout.write(
            self.style.WARNING(
                f"⚠️  About to delete {delete_ip_count} IP record(s) "
                f"and {delete_fingerprint_count} related fingerprint record(s) "
                f"{'(limited)' if limit and limit < total_ip_count else ''}"
            )
        )

        # Delete IPAddress records (will cascade delete related RequestFingerprint records)
        _, deletion_info = queryset.delete()

        # Get the actual counts from deletion_info
        ip_deleted = deletion_info.get("utils.IPAddress", 0)
        fingerprint_deleted = deletion_info.get("utils.RequestFingerprint", 0)

        self.stdout.write("")
        self.stdout.write(
            self.style.SUCCESS(
                f"✅ Successfully deleted {ip_deleted} IP record(s) "
                f"and {fingerprint_deleted} related fingerprint record(s)"
            )
        )

        if limit and total_ip_count > limit:
            remaining_ips = total_ip_count - ip_deleted
            remaining_fingerprints = total_fingerprint_count - fingerprint_deleted
            self.stdout.write(
                self.style.WARNING(
                    f"ℹ️  {remaining_ips} local IP record(s) and "
                    f"{remaining_fingerprints} related fingerprint record(s) remaining "
                    f"(use --limit or run again to delete more)"
                )
            )
