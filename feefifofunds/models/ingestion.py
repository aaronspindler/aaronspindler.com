import hashlib
import uuid
from datetime import datetime, timedelta

from django.core.validators import MinValueValidator
from django.db import models

from utils.models import TimestampedModel


class IngestionJob(TimestampedModel):
    class Status(models.TextChoices):
        PENDING = "PENDING", "Pending"
        RUNNING = "RUNNING", "Running"
        COMPLETED = "COMPLETED", "Completed"
        FAILED = "FAILED", "Failed"
        PAUSED = "PAUSED", "Paused"

    job_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    tier = models.CharField(max_length=20, help_text="Asset tier (TIER1, TIER2, etc.)")
    intervals = models.JSONField(help_text="List of interval minutes to ingest (e.g., [60, 1440])")
    start_date = models.DateField(help_text="Ingestion start date")
    end_date = models.DateField(help_text="Ingestion end date")

    csv_source_dir = models.CharField(max_length=500, help_text="Directory containing CSV files")
    api_backfill_enabled = models.BooleanField(default=True, help_text="Enable API backfilling for gaps")
    auto_gap_fill = models.BooleanField(default=True, help_text="Automatically fill API-fillable gaps")

    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING, db_index=True)

    started_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    paused_at = models.DateTimeField(null=True, blank=True)

    assets_count = models.IntegerField(default=0, help_text="Number of assets to ingest")
    total_files = models.IntegerField(default=0, help_text="Total CSV files to process")
    files_ingested = models.IntegerField(default=0, help_text="CSV files successfully processed")
    files_failed = models.IntegerField(default=0, help_text="CSV files that failed")
    files_skipped = models.IntegerField(default=0, help_text="CSV files skipped (already ingested)")
    records_ingested = models.BigIntegerField(default=0, help_text="Total OHLCV records ingested")

    gaps_detected = models.IntegerField(default=0, help_text="Number of gaps detected")
    gaps_filled = models.IntegerField(default=0, help_text="Number of gaps filled via API")
    gaps_unfillable = models.IntegerField(default=0, help_text="Number of unfillable gaps (>720 candles)")

    # Error tracking
    error_message = models.TextField(null=True, blank=True)
    error_traceback = models.TextField(null=True, blank=True)

    class Meta:
        db_table = "feefifofunds_ingestion_job"
        ordering = ["-started_at"]
        indexes = [
            models.Index(fields=["tier", "status"]),
            models.Index(fields=["started_at"]),
        ]

    def __str__(self) -> str:
        return f"IngestionJob {self.job_id} ({self.tier}, {self.status})"

    @property
    def duration(self) -> timedelta | None:
        if not self.started_at:
            return None
        end_time = self.completed_at or datetime.now()
        return end_time - self.started_at

    @property
    def progress_pct(self) -> float:
        if self.total_files == 0:
            return 0.0
        return (self.files_ingested / self.total_files) * 100

    def mark_running(self):
        self.status = self.Status.RUNNING
        self.save(update_fields=["status"])

    def mark_completed(self):
        self.status = self.Status.COMPLETED
        self.completed_at = datetime.now()
        self.save(update_fields=["status", "completed_at"])

    def mark_failed(self, error: Exception):
        self.status = self.Status.FAILED
        self.completed_at = datetime.now()
        self.error_message = str(error)
        self.error_traceback = error.__traceback__ if hasattr(error, "__traceback__") else None
        self.save(update_fields=["status", "completed_at", "error_message", "error_traceback"])

    def mark_paused(self):
        self.status = self.Status.PAUSED
        self.paused_at = datetime.now()
        self.save(update_fields=["status", "paused_at"])


class FileIngestionRecord(TimestampedModel):
    class Status(models.TextChoices):
        PENDING = "PENDING", "Pending"
        INGESTING = "INGESTING", "Ingesting"
        COMPLETED = "COMPLETED", "Completed"
        FAILED = "FAILED", "Failed"
        SKIPPED = "SKIPPED", "Skipped - Already Ingested"

    job = models.ForeignKey(IngestionJob, on_delete=models.CASCADE, related_name="file_records")

    file_path = models.CharField(max_length=500, unique=True, help_text="Absolute path to CSV file")
    file_name = models.CharField(max_length=255, help_text="Original filename")
    file_size_bytes = models.BigIntegerField(validators=[MinValueValidator(0)])
    file_hash = models.CharField(
        max_length=64, help_text="SHA-256 hash of file contents (for duplicate detection)", db_index=True
    )

    asset = models.ForeignKey("Asset", on_delete=models.CASCADE, related_name="ingestion_records")
    interval_minutes = models.IntegerField(validators=[MinValueValidator(1)])

    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING, db_index=True)

    records_count = models.BigIntegerField(default=0, help_text="Number of OHLCV records in file")
    date_range_start = models.DateTimeField(null=True, blank=True, help_text="Earliest timestamp in file")
    date_range_end = models.DateTimeField(null=True, blank=True, help_text="Latest timestamp in file")

    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    # Error tracking
    error_message = models.TextField(null=True, blank=True)

    class Meta:
        db_table = "feefifofunds_file_ingestion_record"
        ordering = ["job", "file_name"]
        indexes = [
            models.Index(fields=["job", "status"]),
            models.Index(fields=["asset", "interval_minutes"]),
            models.Index(fields=["file_hash"]),
        ]

    def __str__(self) -> str:
        return f"FileIngestionRecord {self.file_name} ({self.status})"

    @classmethod
    def calculate_file_hash(cls, file_path: str) -> str:
        sha256 = hashlib.sha256()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                sha256.update(chunk)
        return sha256.hexdigest()

    @classmethod
    def is_file_already_ingested(cls, file_path: str) -> bool:
        file_hash = cls.calculate_file_hash(file_path)
        return cls.objects.filter(file_hash=file_hash, status=cls.Status.COMPLETED).exists()

    def mark_ingesting(self):
        self.status = self.Status.INGESTING
        self.started_at = datetime.now()
        self.save(update_fields=["status", "started_at"])

    def mark_completed(self, records_count: int, date_range_start: datetime, date_range_end: datetime):
        self.status = self.Status.COMPLETED
        self.completed_at = datetime.now()
        self.records_count = records_count
        self.date_range_start = date_range_start
        self.date_range_end = date_range_end
        self.save(update_fields=["status", "completed_at", "records_count", "date_range_start", "date_range_end"])

    def mark_failed(self, error: str):
        self.status = self.Status.FAILED
        self.completed_at = datetime.now()
        self.error_message = error
        self.save(update_fields=["status", "completed_at", "error_message"])

    def mark_skipped(self, reason: str = "Already ingested"):
        self.status = self.Status.SKIPPED
        self.error_message = reason
        self.save(update_fields=["status", "error_message"])


class DataCoverageRange(TimestampedModel):
    class Source(models.TextChoices):
        CSV = "CSV", "CSV File"
        API = "API", "Kraken API"
        MIXED = "MIXED", "Mixed Sources"

    asset = models.ForeignKey("Asset", on_delete=models.CASCADE, related_name="coverage_ranges")
    interval_minutes = models.IntegerField(validators=[MinValueValidator(1)])

    start_date = models.DateTimeField(help_text="First timestamp in coverage range")
    end_date = models.DateTimeField(help_text="Last timestamp in coverage range")

    source = models.CharField(max_length=20, choices=Source.choices, default=Source.CSV)
    record_count = models.BigIntegerField(validators=[MinValueValidator(0)], help_text="Number of candles in range")

    last_verified = models.DateTimeField(auto_now=True, help_text="Last time this range was verified in QuestDB")

    class Meta:
        db_table = "feefifofunds_data_coverage_range"
        ordering = ["asset", "interval_minutes", "start_date"]
        indexes = [
            models.Index(fields=["asset", "interval_minutes", "start_date"]),
            models.Index(fields=["asset", "interval_minutes", "end_date"]),
        ]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(end_date__gte=models.F("start_date")), name="end_date_after_start_date"
            )
        ]

    def __str__(self) -> str:
        return f"Coverage {self.asset.ticker} {self.interval_minutes}min: {self.start_date} to {self.end_date}"

    @classmethod
    def merge_overlapping_ranges(cls, asset, interval_minutes: int):
        ranges = list(cls.objects.filter(asset=asset, interval_minutes=interval_minutes).order_by("start_date"))

        if len(ranges) <= 1:
            return ranges  # Fixed: Return consistent type (list) instead of implicit None

        merged = []
        current = ranges[0]

        for next_range in ranges[1:]:
            interval_delta = timedelta(minutes=interval_minutes)
            if next_range.start_date <= current.end_date + interval_delta:
                current.end_date = max(current.end_date, next_range.end_date)
                current.record_count += next_range.record_count

                if current.source != next_range.source:
                    current.source = cls.Source.MIXED

                next_range.delete()
            else:
                current.save()
                merged.append(current)
                current = next_range

        current.save()
        merged.append(current)

        return merged


class GapRecord(TimestampedModel):
    class Status(models.TextChoices):
        DETECTED = "DETECTED", "Detected"
        BACKFILLING = "BACKFILLING", "Backfilling"
        FILLED = "FILLED", "Filled"
        UNFILLABLE = "UNFILLABLE", "Unfillable - Requires CSV"
        FAILED = "FAILED", "Failed"

    asset = models.ForeignKey("Asset", on_delete=models.CASCADE, related_name="gaps")
    interval_minutes = models.IntegerField(validators=[MinValueValidator(1)])

    gap_start = models.DateTimeField(help_text="Start of gap (missing data)")
    gap_end = models.DateTimeField(help_text="End of gap (missing data)")
    missing_candles = models.IntegerField(validators=[MinValueValidator(1)], help_text="Number of missing candles")

    is_api_fillable = models.BooleanField(
        default=False, help_text="Can this gap be filled via Kraken API (within 720-candle limit)?"
    )
    overflow_candles = models.IntegerField(default=0, help_text="How many candles beyond 720-candle API limit")
    candles_from_today = models.IntegerField(default=0, help_text="Number of candles from gap_start to today")

    status = models.CharField(max_length=20, choices=Status.choices, default=Status.DETECTED, db_index=True)

    detected_at = models.DateTimeField(auto_now_add=True)
    backfill_attempted_at = models.DateTimeField(null=True, blank=True)
    filled_at = models.DateTimeField(null=True, blank=True)

    required_csv_file = models.CharField(
        max_length=255, null=True, blank=True, help_text="Suggested CSV filename to download from Kraken"
    )

    # Error tracking
    error_message = models.TextField(null=True, blank=True)

    class Meta:
        db_table = "feefifofunds_gap_record"
        ordering = ["asset", "interval_minutes", "gap_start"]
        indexes = [
            models.Index(fields=["asset", "interval_minutes", "status"]),
            models.Index(fields=["status", "is_api_fillable"]),
            models.Index(fields=["detected_at"]),
        ]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(gap_end__gt=models.F("gap_start")), name="gap_end_after_gap_start"
            )
        ]

    def __str__(self) -> str:
        return (
            f"Gap {self.asset.ticker} {self.interval_minutes}min: "
            f"{self.gap_start} to {self.gap_end} ({self.missing_candles} candles)"
        )

    @classmethod
    def calculate_api_fillability(
        cls, interval_minutes: int, gap_start: datetime, now: datetime | None = None
    ) -> tuple[bool, int, int]:
        if now is None:
            now = datetime.now()

        candles_from_today = int((now - gap_start).total_seconds() / (interval_minutes * 60))

        is_api_fillable = candles_from_today <= 720
        overflow_candles = max(0, candles_from_today - 720)

        return is_api_fillable, overflow_candles, candles_from_today

    def mark_backfilling(self):
        self.status = self.Status.BACKFILLING
        self.backfill_attempted_at = datetime.now()
        self.save(update_fields=["status", "backfill_attempted_at"])

    def mark_filled(self):
        self.status = self.Status.FILLED
        self.filled_at = datetime.now()
        self.save(update_fields=["status", "filled_at"])

    def mark_unfillable(self, suggested_csv: str):
        self.status = self.Status.UNFILLABLE
        self.required_csv_file = suggested_csv
        self.save(update_fields=["status", "required_csv_file"])

    def mark_failed(self, error: str):
        self.status = self.Status.FAILED
        self.error_message = error
        self.save(update_fields=["status", "error_message"])
