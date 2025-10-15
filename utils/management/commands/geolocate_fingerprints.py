"""
Management command to geolocate IP addresses for RequestFingerprint records.

This command batch processes IP addresses using the ip-api.com free tier API
to add geographic location data (city, country, coordinates, timezone, ISP, etc.)
to RequestFingerprint records.

Usage:
    python manage.py geolocate_fingerprints
    python manage.py geolocate_fingerprints --limit 100
    python manage.py geolocate_fingerprints --force  # Re-geolocate all records
    python manage.py geolocate_fingerprints --batch-size 50  # Custom batch size

Features:
    - Processes only records without geo_data (unless --force is used)
    - Automatically filters local/private IPs (127.0.0.1, 10.x.x.x, etc.)
    - Respects API rate limits (15 requests/minute, 100 IPs per batch)
    - Updates all records sharing the same IP address
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

from utils.models.security import RequestFingerprint
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

    def handle(self, *args, **options):
        limit = options.get("limit")
        force = options.get("force", False)
        batch_size = options.get("batch_size", 100)

        # Query for records without geolocation data (or all if --force)
        if force:
            queryset = RequestFingerprint.objects.all()
            self.stdout.write(self.style.WARNING("🔄 Force mode: Re-geolocating all records"))
        else:
            queryset = RequestFingerprint.objects.filter(geo_data__isnull=True)

        if limit:
            queryset = queryset[:limit]

        # Get distinct IP addresses
        ip_addresses = list(queryset.values_list("ip_address", flat=True).distinct())

        if not ip_addresses:
            self.stdout.write(self.style.SUCCESS("✅ No IP addresses to geolocate"))
            return

        self.stdout.write(f"📍 Geolocating {len(ip_addresses)} unique IP addresses")
        self.stdout.write(f"📦 Batch size: {batch_size}")

        # Geolocate in batches
        results = geolocate_ips_batch(ip_addresses, batch_size=batch_size)

        # Update records with geolocation data
        success_count = 0
        failed_count = 0

        self.stdout.write("💾 Updating database records...")

        for ip_address, geo_data in results.items():
            if geo_data:
                # Update all records with this IP address
                updated = RequestFingerprint.objects.filter(ip_address=ip_address).update(geo_data=geo_data)
                success_count += updated
                self.stdout.write(
                    self.style.SUCCESS(
                        f"  ✓ {ip_address} -> {geo_data.get('city', 'Unknown')}, "
                        f"{geo_data.get('country', 'Unknown')} "
                        f"({updated} records updated)"
                    )
                )
            else:
                failed_count += RequestFingerprint.objects.filter(ip_address=ip_address).count()
                self.stdout.write(self.style.WARNING(f"  ✗ {ip_address} -> Failed to geolocate"))

        self.stdout.write("")
        self.stdout.write(self.style.SUCCESS(f"✅ Successfully geolocated {success_count} records"))
        if failed_count > 0:
            self.stdout.write(self.style.WARNING(f"⚠️  Failed to geolocate {failed_count} records"))
