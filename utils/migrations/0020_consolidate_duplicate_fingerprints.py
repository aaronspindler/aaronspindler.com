"""
Data migration to consolidate Fingerprint objects with duplicate hashes.

This prepares for adding a unique constraint on the hash field by:
1. Grouping fingerprints by hash
2. Keeping the oldest fingerprint (earliest first_seen) as the canonical one
3. Reassigning all RequestFingerprint references to the canonical fingerprint
4. Updating the canonical fingerprint's last_seen to the max of all duplicates
5. Deleting duplicate fingerprints
"""

from django.db import migrations
from django.db.models import Count, Min, Max


def consolidate_duplicate_fingerprints(apps, schema_editor):
    Fingerprint = apps.get_model("utils", "Fingerprint")
    RequestFingerprint = apps.get_model("utils", "RequestFingerprint")

    # Find all hashes that have duplicates
    duplicate_hashes = list(
        Fingerprint.objects.values("hash")
        .annotate(count=Count("id"))
        .filter(count__gt=1)
        .values_list("hash", flat=True)
    )

    total_hashes = len(duplicate_hashes)
    if total_hashes == 0:
        print("\nNo duplicate fingerprints found.")
        return

    print(f"\nFound {total_hashes} hashes with duplicates to consolidate...")

    total_duplicates_removed = 0
    total_requests_reassigned = 0

    for i, hash_value in enumerate(duplicate_hashes, 1):
        # Get all fingerprints with this hash, ordered by first_seen then id
        fingerprints = list(
            Fingerprint.objects.filter(hash=hash_value).order_by("first_seen", "id")
        )

        if len(fingerprints) <= 1:
            continue

        # Keep the first one (earliest first_seen) as canonical
        canonical = fingerprints[0]
        duplicates = fingerprints[1:]

        # Get the max last_seen across all duplicates (including canonical)
        max_last_seen = max(fp.last_seen for fp in fingerprints)

        # Update canonical's last_seen if any duplicate was seen more recently
        if max_last_seen > canonical.last_seen:
            canonical.last_seen = max_last_seen
            canonical.save(update_fields=["last_seen"])

        # Reassign all RequestFingerprints from duplicates to canonical
        duplicate_ids = [fp.id for fp in duplicates]
        requests_updated = RequestFingerprint.objects.filter(
            fingerprint_obj_id__in=duplicate_ids
        ).update(fingerprint_obj=canonical)

        total_requests_reassigned += requests_updated

        # Delete the duplicates
        deleted_count, _ = Fingerprint.objects.filter(id__in=duplicate_ids).delete()
        total_duplicates_removed += deleted_count

        # Progress output every 100 hashes or on the last one
        if i % 100 == 0 or i == total_hashes:
            print(f"  Processed {i}/{total_hashes} hashes...")

    print(
        f"\nDone! Consolidated {total_duplicates_removed} duplicate fingerprints, "
        f"reassigned {total_requests_reassigned} request fingerprints."
    )


def reverse_consolidate(apps, schema_editor):
    # This migration cannot be reversed since we're deleting data
    # The forward migration is safe but irreversible
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("utils", "0019_rename_hash_without_ip_to_hash"),
    ]

    operations = [
        migrations.RunPython(
            consolidate_duplicate_fingerprints,
            reverse_code=reverse_consolidate,
        ),
    ]
