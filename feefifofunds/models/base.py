"""
Base model classes for FeeFiFoFunds application.

Provides common fields and functionality for all models.
"""

from django.db import models
from django.utils import timezone


class TimestampedModel(models.Model):
    """
    Abstract base model that provides timestamp fields.

    Attributes:
        created_at: Timestamp when the record was created
        updated_at: Timestamp when the record was last updated
    """

    created_at = models.DateTimeField(
        default=timezone.now,
        editable=False,
        db_index=True,
        help_text="Timestamp when this record was created",
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        db_index=True,
        help_text="Timestamp when this record was last updated",
    )

    class Meta:
        abstract = True
        ordering = ["-created_at"]


class SoftDeleteModel(models.Model):
    """
    Abstract base model that provides soft delete functionality.

    Instead of hard deleting records, marks them as inactive for audit trail.

    Attributes:
        is_active: Whether the record is active (not soft-deleted)
        deleted_at: Timestamp when the record was soft-deleted
    """

    is_active = models.BooleanField(
        default=True,
        db_index=True,
        help_text="Whether this record is active",
    )
    deleted_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Timestamp when this record was soft-deleted",
    )

    class Meta:
        abstract = True

    def delete(self, using=None, keep_parents=False, soft=True):
        """
        Soft delete the object by default.

        Args:
            using: Database alias to use
            keep_parents: Whether to keep parent records
            soft: If True, performs soft delete. If False, performs hard delete.
        """
        if soft:
            self.is_active = False
            self.deleted_at = timezone.now()
            self.save(using=using, update_fields=["is_active", "deleted_at"])
        else:
            super().delete(using=using, keep_parents=keep_parents)

    def restore(self):
        """Restore a soft-deleted object."""
        self.is_active = True
        self.deleted_at = None
        self.save(update_fields=["is_active", "deleted_at"])
