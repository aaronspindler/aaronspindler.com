"""
Management command to geolocate IP addresses.

This command batch processes IP addresses using the ip-api.com free tier API
to add geographic location data (city, country, coordinates, timezone, ISP, etc.)
to the IPAddress model. All RequestFingerprint records sharing the same IP
automatically benefit from the geolocation data via the ForeignKey relationship.

Usage:
    python manage.py geolocate_fingerprints
    python manage.py geolocate_fingerprints --limit 100
    python manage.py geolocate_fingerprints --force  # Re-geolocate all records
    python manage.py geolocate_fingerprints --batch-size 50  # Custom batch size
    python manage.py geolocate_fingerprints --yes  # Skip confirmation (for cron/Celery)

Features:
    - Works with normalized IPAddress model (one geo_data per IP, not per request)
    - Processes only IPAddress records without geo_data (unless --force is used)
    - Automatically filters local/private IPs (127.0.0.1, 10.x.x.x, etc.)
    - Respects API rate limits (15 requests/minute, 100 IPs per batch)
    - Updates IPAddress records (all RequestFingerprints automatically benefit via ForeignKey)
    - Shows statistics before processing (IPs vs total fingerprints affected)
    - Waits for confirmation before proceeding (use --yes to skip)
    - Provides detailed progress feedback

API Rate Limits (ip-api.com free tier):
    - Batch endpoint: 15 requests per minute
    - Each batch can contain up to 100 IP addresses
    - Total: ~1,500 IPs per minute with batching

Recommended Usage:
    - Run periodically via cron or Celery Beat to process new records
    - DO NOT run during request processing (causes latency)
    - Use --limit to avoid hitting API rate limits during manual runs

Documentation:
    See CLAUDE.md and README.md for complete documentation
"""

from django.core.management.base import BaseCommand

from utils.models.security import IPAddress
from utils.security import geolocate_ips_batch


class Command(BaseCommand):
    help = "Geolocate IP addresses for RequestFingerprint records without geolocation data"

    def add_arguments(self, parser):
        parser.add_argument(
            "--limit",
            type=int,
            help="Maximum number of records to process",
        )
        parser.add_argument(
            "--force",
            action="store_true",
            help="Re-geolocate all records, even those with existing geo_data",
        )
        parser.add_argument(
            "--batch-size",
            type=int,
            default=100,
            help="Number of IPs per batch (default: 100)",
        )
        parser.add_argument(
            "--yes",
            "-y",
            action="store_true",
            help="Skip confirmation prompt (for automated runs)",
        )

    def handle(self, *args, **options):
        limit = options.get("limit")
        force = options.get("force", False)
        batch_size = options.get("batch_size", 100)
        skip_confirmation = options.get("yes", False)

        # Query IPAddress records without geolocation data (or all if --force)
        if force:
            queryset = IPAddress.objects.all()
            self.stdout.write(self.style.WARNING("🔄 Force mode: Re-geolocating all IP addresses"))
        else:
            queryset = IPAddress.objects.filter(geo_data__isnull=True)

        if limit:
            queryset = queryset[:limit]

        # Get IP addresses to geolocate
        ip_records = list(queryset)
        ip_addresses_str = [ip.ip_address for ip in ip_records]

        if not ip_addresses_str:
            self.stdout.write(self.style.SUCCESS("✅ No IP addresses to geolocate"))
            return

        # Count how many RequestFingerprints will benefit
        total_fingerprints = sum(ip.request_fingerprints.count() for ip in ip_records)

        # Show statistics before processing
        self.stdout.write(f"📊 Found {len(ip_records)} IP address(es) without geolocation data")
        self.stdout.write(f"🔗 These IPs are used by {total_fingerprints} RequestFingerprint record(s)")
        self.stdout.write(f"📦 Batch size: {batch_size}")
        self.stdout.write("")  # Blank line for readability

        # Wait for user confirmation (unless --yes flag is used)
        if not skip_confirmation:
            try:
                input("Press Enter to continue with geolocation...")
            except KeyboardInterrupt:
                self.stdout.write(self.style.WARNING("\n\n⚠️  Cancelled by user"))
                return

            self.stdout.write("")  # Blank line after confirmation

        # Geolocate IPs via API
        self.stdout.write("🌐 Geolocating IP addresses via API...")
        results = geolocate_ips_batch(ip_addresses_str, batch_size=batch_size)

        # Update IPAddress records with geolocation data
        success_count = 0
        failed_count = 0

        self.stdout.write("💾 Updating IPAddress records...")
        for ip_str, geo_data in results.items():
            if geo_data:
                # Update the IPAddress record
                IPAddress.objects.filter(ip_address=ip_str).update(geo_data=geo_data)
                ip_obj = IPAddress.objects.get(ip_address=ip_str)
                fingerprint_count = ip_obj.request_fingerprints.count()
                success_count += 1

                self.stdout.write(
                    self.style.SUCCESS(
                        f"  ✓ {ip_str} -> {geo_data.get('city', 'Unknown')}, "
                        f"{geo_data.get('country', 'Unknown')} "
                        f"({fingerprint_count} fingerprint(s) updated)"
                    )
                )
            else:
                ip_obj = IPAddress.objects.filter(ip_address=ip_str).first()
                if ip_obj:
                    fingerprint_count = ip_obj.request_fingerprints.count()
                    failed_count += 1
                    self.stdout.write(
                        self.style.WARNING(
                            f"  ✗ {ip_str} -> Failed to geolocate "
                            f"({fingerprint_count} fingerprint(s) remain without geo_data)"
                        )
                    )

        self.stdout.write("")
        self.stdout.write(self.style.SUCCESS(f"✅ Successfully geolocated {success_count} IP address(es)"))
        if failed_count > 0:
            self.stdout.write(self.style.WARNING(f"⚠️  Failed to geolocate {failed_count} IP address(es)"))
