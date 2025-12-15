from django.core.management.base import BaseCommand

from utils.models.security import IPAddress, RequestFingerprint
from utils.security import is_reserved_ip


class Command(BaseCommand):
    help = "Remove IPAddress records (and their related RequestFingerprint records) with local/private IP addresses"

    def handle(self, *args, **options):
        # Get all IPAddress records
        all_ip_addresses = IPAddress.objects.all()

        # Filter for local IPs
        local_ip_objs = [ip_obj for ip_obj in all_ip_addresses if is_reserved_ip(ip_obj.ip_address)]

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

        # Confirm deletion
        self.stdout.write(
            self.style.WARNING(
                f"⚠️  About to delete {delete_ip_count} IP record(s) "
                f"and {delete_fingerprint_count} related fingerprint record(s) "
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
