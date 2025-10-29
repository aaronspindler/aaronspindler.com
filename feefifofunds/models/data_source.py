"""
Data source models - track external API providers and synchronization history.

These models support FUND-004: Implement Data Source Models
"""

from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.utils import timezone

from .base import SoftDeleteModel, TimestampedModel


class DataSource(TimestampedModel, SoftDeleteModel):
    """
    Represents an external data provider/API source.

    Tracks configuration, rate limits, and status for each data provider.
    """

    class SourceType(models.TextChoices):
        """Types of data sources."""

        API = "API", "REST API"
        WEBSOCKET = "WS", "WebSocket"
        FILE = "FILE", "File Upload"
        SCRAPER = "SCRAPER", "Web Scraper"
        DATABASE = "DB", "Database"

    class Status(models.TextChoices):
        """Status of the data source."""

        ACTIVE = "ACTIVE", "Active"
        INACTIVE = "INACTIVE", "Inactive"
        ERROR = "ERROR", "Error"
        RATE_LIMITED = "RATE_LIMITED", "Rate Limited"
        MAINTENANCE = "MAINTENANCE", "Under Maintenance"

    # Source identification
    name = models.CharField(
        max_length=100,
        unique=True,
        db_index=True,
        help_text="Name of the data source (e.g., 'alpha_vantage', 'polygon', 'finnhub')",
    )
    display_name = models.CharField(
        max_length=255,
        help_text="Display name for UI",
    )
    source_type = models.CharField(
        max_length=10,
        choices=SourceType.choices,
        default=SourceType.API,
        help_text="Type of data source",
    )
    description = models.TextField(
        blank=True,
        help_text="Description of this data source and what it provides",
    )

    # Configuration
    base_url = models.URLField(
        max_length=500,
        blank=True,
        help_text="Base URL for API",
    )
    api_key_required = models.BooleanField(
        default=False,
        help_text="Whether this source requires an API key",
    )
    documentation_url = models.URLField(
        max_length=500,
        blank=True,
        help_text="URL to API documentation",
    )

    # Rate limiting
    rate_limit_requests = models.IntegerField(
        null=True,
        blank=True,
        validators=[MinValueValidator(1)],
        help_text="Maximum number of requests allowed",
    )
    rate_limit_period_seconds = models.IntegerField(
        null=True,
        blank=True,
        validators=[MinValueValidator(1)],
        help_text="Time period for rate limit in seconds",
    )
    requests_today = models.IntegerField(
        default=0,
        validators=[MinValueValidator(0)],
        help_text="Number of requests made today",
    )
    last_request_time = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Timestamp of last request",
    )

    # Status and health
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.ACTIVE,
        db_index=True,
        help_text="Current status of the data source",
    )
    last_successful_sync = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Timestamp of last successful data sync",
    )
    last_error = models.TextField(
        blank=True,
        help_text="Last error message encountered",
    )
    last_error_time = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Timestamp of last error",
    )
    consecutive_failures = models.IntegerField(
        default=0,
        validators=[MinValueValidator(0)],
        help_text="Number of consecutive failures",
    )

    # Priority and reliability
    priority = models.IntegerField(
        default=50,
        validators=[MinValueValidator(1), MaxValueValidator(100)],
        db_index=True,
        help_text="Priority for this source (1-100, higher = more preferred)",
    )
    reliability_score = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=100.00,
        validators=[MinValueValidator(0.00), MaxValueValidator(100.00)],
        help_text="Reliability score (0-100) based on historical success rate",
    )

    # Data coverage
    supports_historical_data = models.BooleanField(
        default=True,
        help_text="Whether this source provides historical data",
    )
    supports_realtime_data = models.BooleanField(
        default=False,
        help_text="Whether this source provides real-time data",
    )
    supports_holdings = models.BooleanField(
        default=False,
        help_text="Whether this source provides holdings data",
    )
    supports_fundamentals = models.BooleanField(
        default=False,
        help_text="Whether this source provides fundamental data",
    )

    # Cost tracking
    is_free = models.BooleanField(
        default=True,
        help_text="Whether this source is free to use",
    )
    monthly_cost = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Monthly cost in USD",
    )

    class Meta:
        db_table = "feefifofunds_datasource"
        verbose_name = "Data Source"
        verbose_name_plural = "Data Sources"
        ordering = ["-priority", "name"]
        indexes = [
            models.Index(fields=["-priority", "status"]),
            models.Index(fields=["status", "-last_successful_sync"]),
        ]

    def __str__(self) -> str:
        """String representation."""
        return f"{self.display_name} ({self.name})"

    def can_make_request(self) -> bool:
        """Check if we can make a request to this source (rate limiting)."""
        if self.status != self.Status.ACTIVE:
            return False

        if not self.rate_limit_requests or not self.rate_limit_period_seconds:
            return True

        # Check if we've exceeded rate limit
        if self.last_request_time:
            time_since_last_request = (timezone.now() - self.last_request_time).total_seconds()
            if time_since_last_request < self.rate_limit_period_seconds:
                # Within rate limit window - check request count
                return self.requests_today < self.rate_limit_requests

        return True

    def record_request(self, success: bool = True, error_message: str = ""):
        """
        Record a request to this data source.

        Args:
            success: Whether the request was successful
            error_message: Error message if request failed
        """
        self.last_request_time = timezone.now()
        self.requests_today += 1

        if success:
            self.last_successful_sync = timezone.now()
            self.consecutive_failures = 0
            self.last_error = ""
            if self.status == self.Status.ERROR:
                self.status = self.Status.ACTIVE
        else:
            self.consecutive_failures += 1
            self.last_error = error_message
            self.last_error_time = timezone.now()
            if self.consecutive_failures >= 5:
                self.status = self.Status.ERROR

        # Update reliability score (exponential moving average)
        alpha = 0.1  # Smoothing factor
        current_success_rate = 1.0 if success else 0.0
        old_score = float(self.reliability_score)
        self.reliability_score = alpha * (current_success_rate * 100) + (1 - alpha) * old_score

        self.save(
            update_fields=[
                "last_request_time",
                "requests_today",
                "last_successful_sync",
                "consecutive_failures",
                "last_error",
                "last_error_time",
                "status",
                "reliability_score",
            ]
        )

    def reset_daily_requests(self):
        """Reset the daily request counter (should be called daily)."""
        self.requests_today = 0
        self.save(update_fields=["requests_today"])


class DataSync(TimestampedModel):
    """
    Records synchronization attempts and results.

    Provides audit trail for data fetching operations.
    """

    class SyncType(models.TextChoices):
        """Type of sync operation."""

        FUND_INFO = "FUND_INFO", "Fund Information"
        PRICES = "PRICES", "Price Data"
        HOLDINGS = "HOLDINGS", "Holdings"
        FUNDAMENTALS = "FUNDAMENTALS", "Fundamental Data"
        METRICS = "METRICS", "Calculated Metrics"

    class Status(models.TextChoices):
        """Status of the sync operation."""

        PENDING = "PENDING", "Pending"
        IN_PROGRESS = "IN_PROGRESS", "In Progress"
        SUCCESS = "SUCCESS", "Success"
        PARTIAL_SUCCESS = "PARTIAL", "Partial Success"
        FAILED = "FAILED", "Failed"

    # Relationship to data source
    data_source = models.ForeignKey(
        DataSource,
        on_delete=models.CASCADE,
        related_name="sync_history",
        db_index=True,
        help_text="Data source used for this sync",
    )

    # Relationship to fund (optional - some syncs may be for multiple funds)
    fund = models.ForeignKey(
        "feefifofunds.Fund",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="sync_history",
        db_index=True,
        help_text="Fund this sync was for (if applicable)",
    )

    # Sync details
    sync_type = models.CharField(
        max_length=20,
        choices=SyncType.choices,
        db_index=True,
        help_text="Type of data being synced",
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
        db_index=True,
        help_text="Status of the sync",
    )

    # Timing
    started_at = models.DateTimeField(
        auto_now_add=True,
        help_text="When the sync started",
    )
    completed_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When the sync completed",
    )
    duration_seconds = models.IntegerField(
        null=True,
        blank=True,
        help_text="Duration of sync in seconds",
    )

    # Results
    records_fetched = models.IntegerField(
        default=0,
        validators=[MinValueValidator(0)],
        help_text="Number of records fetched",
    )
    records_created = models.IntegerField(
        default=0,
        validators=[MinValueValidator(0)],
        help_text="Number of new records created",
    )
    records_updated = models.IntegerField(
        default=0,
        validators=[MinValueValidator(0)],
        help_text="Number of existing records updated",
    )
    records_failed = models.IntegerField(
        default=0,
        validators=[MinValueValidator(0)],
        help_text="Number of records that failed validation",
    )

    # Error handling
    error_message = models.TextField(
        blank=True,
        help_text="Error message if sync failed",
    )
    error_details = models.JSONField(
        default=dict,
        blank=True,
        help_text="Detailed error information (structured data)",
    )

    # Request details
    request_params = models.JSONField(
        default=dict,
        blank=True,
        help_text="Parameters used for the request",
    )
    response_metadata = models.JSONField(
        default=dict,
        blank=True,
        help_text="Metadata from the API response",
    )

    # Celery task tracking (if applicable)
    celery_task_id = models.CharField(
        max_length=255,
        blank=True,
        db_index=True,
        help_text="Celery task ID if run asynchronously",
    )

    class Meta:
        db_table = "feefifofunds_datasync"
        verbose_name = "Data Sync"
        verbose_name_plural = "Data Syncs"
        ordering = ["-started_at"]
        indexes = [
            models.Index(fields=["-started_at"]),
            models.Index(fields=["data_source", "-started_at"]),
            models.Index(fields=["fund", "-started_at"]),
            models.Index(fields=["status", "-started_at"]),
            models.Index(fields=["sync_type", "-started_at"]),
            models.Index(fields=["celery_task_id"]),
        ]

    def __str__(self) -> str:
        """String representation."""
        fund_str = f" for {self.fund.ticker}" if self.fund else ""
        return f"{self.sync_type} from {self.data_source.name}{fund_str} - {self.status}"

    def mark_complete(self, success: bool = True, error_message: str = ""):
        """
        Mark the sync as complete.

        Args:
            success: Whether the sync was successful
            error_message: Error message if sync failed
        """
        self.completed_at = timezone.now()
        if self.started_at:
            self.duration_seconds = int((self.completed_at - self.started_at).total_seconds())

        if success:
            if self.records_failed > 0:
                self.status = self.Status.PARTIAL_SUCCESS
            else:
                self.status = self.Status.SUCCESS
        else:
            self.status = self.Status.FAILED
            self.error_message = error_message

        self.save(update_fields=["completed_at", "duration_seconds", "status", "error_message"])

    @classmethod
    def get_recent_syncs(cls, data_source=None, fund=None, sync_type=None, limit=20):
        """
        Get recent sync history.

        Args:
            data_source: Optional DataSource to filter by
            fund: Optional Fund to filter by
            sync_type: Optional sync type to filter by
            limit: Maximum number of records to return

        Returns:
            QuerySet of DataSync records
        """
        queryset = cls.objects.all()

        if data_source:
            queryset = queryset.filter(data_source=data_source)
        if fund:
            queryset = queryset.filter(fund=fund)
        if sync_type:
            queryset = queryset.filter(sync_type=sync_type)

        return queryset.order_by("-started_at")[:limit]

    @classmethod
    def get_success_rate(cls, data_source=None, sync_type=None, days=30):
        """
        Calculate success rate for syncs.

        Args:
            data_source: Optional DataSource to filter by
            sync_type: Optional sync type to filter by
            days: Number of days to look back

        Returns:
            Success rate as a percentage (0-100)
        """
        from datetime import timedelta

        from django.db.models import Count

        cutoff_date = timezone.now() - timedelta(days=days)
        queryset = cls.objects.filter(started_at__gte=cutoff_date)

        if data_source:
            queryset = queryset.filter(data_source=data_source)
        if sync_type:
            queryset = queryset.filter(sync_type=sync_type)

        stats = queryset.aggregate(
            total=Count("id"),
            successful=Count("id", filter=models.Q(status__in=[cls.Status.SUCCESS, cls.Status.PARTIAL_SUCCESS])),
        )

        if stats["total"] > 0:
            return (stats["successful"] / stats["total"]) * 100
        return 0.0
