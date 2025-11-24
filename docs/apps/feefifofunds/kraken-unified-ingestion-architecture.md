# Unified Kraken Data Ingestion Architecture

## Executive Summary

This document describes a rearchitected Kraken data ingestion system that replaces the current 3-step process (historical CSV → quarterly files → gap backfill) with a **unified, stateful, tier-aware ingestion pipeline**.

### Key Improvements

1. **Single Unified Command**: One command orchestrates the entire ingestion workflow
2. **Persistent State Tracking**: Database-backed progress tracking for resumability
3. **Intelligent Data Source Selection**: Automatic CSV vs API routing based on date ranges and availability
4. **Integrated Gap Detection**: Gaps detected and filled as part of main workflow, not as separate step
5. **Tier-Based Completeness**: Clear metrics showing data completeness for each tier
6. **Incremental Updates**: Support for keeping data current with scheduled runs

---

## Current Architecture Problems

### Problem 1: Three Disconnected Steps
```
Step 1: ingest_sequential (historical CSV)
    ↓
Step 2: ingest_sequential (quarterly files)
    ↓
Step 3: backfill_kraken_gaps (API backfill)
```

**Issues:**
- No coordination between steps
- Manual file management required
- No visibility into overall progress
- Re-running requires moving files back from `ingested/`
- Gap detection happens after ingestion (too late)

### Problem 2: No Persistent State

**Current behavior:**
- No record of what's been ingested
- Can't resume interrupted ingestions
- Can't detect which quarters are missing
- Can't track which gaps have been attempted

### Problem 3: API Limitation Not Handled Upfront

**720-Candle Limit:**
- Daily (1440min): Only ~2 years of history
- Hourly (60min): Only 30 days
- 5-minute: Only ~2.5 days

**Current approach:**
- Ingest all CSV files first
- Detect gaps later
- Try to backfill via API
- Discover some gaps are unfillable (>720 candles ago)
- Manually download CSV for unfillable gaps → repeat process

### Problem 4: No Tier-Based Completeness Visibility

**Questions you can't answer easily:**
- "Do I have complete TIER1 data for the last 5 years?"
- "Which TIER2 assets are missing Q3 2023 data?"
- "Which intervals are complete for TIER1?"

### Problem 5: Quarterly File Management

**Current approach:**
- Assumes files are pre-downloaded and available
- No tracking of which quarters exist
- No automation for downloading missing quarters

---

## Unified Architecture Design

### Overview

```
┌──────────────────────────────────────────────────────────────────┐
│                  Unified Ingestion Command                        │
│  python manage.py ingest_kraken_unified --tier TIER1 --complete  │
└────────────────┬─────────────────────────────────────────────────┘
                 │
                 ▼
         ┌───────────────────┐
         │   State Manager   │
         │  (DB-backed)      │
         └───────┬───────────┘
                 │
        ┌────────┴────────┐
        │                 │
        ▼                 ▼
┌──────────────┐   ┌──────────────┐
│  CSV Ingest  │   │  API Ingest  │
│  (Historical)│   │  (Recent)    │
└──────┬───────┘   └───────┬──────┘
       │                   │
       └───────┬───────────┘
               │
               ▼
       ┌───────────────┐
       │  Gap Detector │
       │  (Integrated) │
       └───────┬───────┘
               │
               ▼
       ┌───────────────┐
       │  Completeness │
       │   Reporter    │
       └───────────────┘
```

### Core Components

#### 1. State Tracking Database Models

**IngestionJob** - Tracks high-level ingestion sessions
```python
class IngestionJob(models.Model):
    """Track unified ingestion jobs"""

    job_id = models.UUIDField(primary_key=True, default=uuid.uuid4)
    tier = models.CharField(max_length=20)  # TIER1, TIER2, etc.
    intervals = models.JSONField()  # [60, 1440]
    start_date = models.DateField()
    end_date = models.DateField()

    status = models.CharField(
        max_length=20,
        choices=[
            ('PENDING', 'Pending'),
            ('RUNNING', 'Running'),
            ('COMPLETED', 'Completed'),
            ('FAILED', 'Failed'),
            ('PAUSED', 'Paused')
        ]
    )

    started_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True)

    # Metrics
    assets_count = models.IntegerField(default=0)
    total_files = models.IntegerField(default=0)
    files_ingested = models.IntegerField(default=0)
    files_failed = models.IntegerField(default=0)
    records_ingested = models.BigIntegerField(default=0)

    # Configuration
    csv_source_dir = models.CharField(max_length=500)
    api_backfill_enabled = models.BooleanField(default=True)
    auto_gap_fill = models.BooleanField(default=True)
```

**FileIngestionRecord** - Tracks individual CSV files
```python
class FileIngestionRecord(models.Model):
    """Track individual CSV file ingestion"""

    job = models.ForeignKey(IngestionJob, on_delete=models.CASCADE)

    file_path = models.CharField(max_length=500, unique=True)
    file_name = models.CharField(max_length=255)
    file_size_bytes = models.BigIntegerField()
    file_hash = models.CharField(max_length=64)  # SHA-256

    asset = models.ForeignKey('Asset', on_delete=models.CASCADE)
    interval_minutes = models.IntegerField()

    status = models.CharField(
        max_length=20,
        choices=[
            ('PENDING', 'Pending'),
            ('INGESTING', 'Ingesting'),
            ('COMPLETED', 'Completed'),
            ('FAILED', 'Failed'),
            ('SKIPPED', 'Skipped'),
        ]
    )

    records_count = models.BigIntegerField(default=0)
    date_range_start = models.DateTimeField(null=True)
    date_range_end = models.DateTimeField(null=True)

    started_at = models.DateTimeField(null=True)
    completed_at = models.DateTimeField(null=True)
    error_message = models.TextField(null=True)

    class Meta:
        indexes = [
            models.Index(fields=['job', 'status']),
            models.Index(fields=['asset', 'interval_minutes']),
        ]
```

**DataCoverageRange** - Tracks what data exists for each asset/interval
```python
class DataCoverageRange(models.Model):
    """Track continuous data coverage ranges"""

    asset = models.ForeignKey('Asset', on_delete=models.CASCADE)
    interval_minutes = models.IntegerField()

    start_date = models.DateTimeField()
    end_date = models.DateTimeField()

    source = models.CharField(
        max_length=20,
        choices=[
            ('CSV', 'CSV File'),
            ('API', 'Kraken API'),
            ('MIXED', 'Mixed Sources')
        ]
    )

    record_count = models.BigIntegerField()
    last_verified = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(fields=['asset', 'interval_minutes', 'start_date']),
        ]
        constraints = [
            models.CheckConstraint(
                check=models.Q(end_date__gte=models.F('start_date')),
                name='end_date_after_start_date'
            )
        ]
```

**GapRecord** - Tracks detected gaps and backfill attempts
```python
class GapRecord(models.Model):
    """Track data gaps and backfill attempts"""

    asset = models.ForeignKey('Asset', on_delete=models.CASCADE)
    interval_minutes = models.IntegerField()

    gap_start = models.DateTimeField()
    gap_end = models.DateTimeField()
    missing_candles = models.IntegerField()

    is_api_fillable = models.BooleanField()
    overflow_candles = models.IntegerField(default=0)

    status = models.CharField(
        max_length=20,
        choices=[
            ('DETECTED', 'Detected'),
            ('BACKFILLING', 'Backfilling'),
            ('FILLED', 'Filled'),
            ('UNFILLABLE', 'Unfillable - Requires CSV'),
            ('FAILED', 'Failed')
        ]
    )

    detected_at = models.DateTimeField(auto_now_add=True)
    backfill_attempted_at = models.DateTimeField(null=True)
    filled_at = models.DateTimeField(null=True)

    required_csv_file = models.CharField(max_length=255, null=True)  # Suggested CSV to download
    error_message = models.TextField(null=True)

    class Meta:
        indexes = [
            models.Index(fields=['asset', 'interval_minutes', 'status']),
            models.Index(fields=['status', 'is_api_fillable']),
        ]
```

#### 2. Unified Ingestion Command

**Command:** `python manage.py ingest_kraken_unified`

**Key Options:**
```bash
# Ingest specific tier to completion
python manage.py ingest_kraken_unified --tier TIER1 --complete

# Ingest tier with specific intervals
python manage.py ingest_kraken_unified --tier TIER1 --intervals 60,1440

# Ingest specific date range
python manage.py ingest_kraken_unified --tier TIER1 \
    --start-date 2020-01-01 --end-date 2024-12-31

# Resume previous job
python manage.py ingest_kraken_unified --resume JOB_UUID

# Incremental update (from last data point to now)
python manage.py ingest_kraken_unified --tier TIER1 --incremental

# Dry-run to see what would be done
python manage.py ingest_kraken_unified --tier TIER1 --dry-run
```

**Workflow:**

```python
class Command(BaseCommand):
    """
    Unified Kraken data ingestion command that orchestrates:
    1. CSV file discovery and ingestion
    2. Gap detection
    3. API backfilling
    4. Completeness reporting
    """

    def handle(self, *args, **options):
        # Step 1: Initialize or resume job
        job = self._initialize_job(options)

        # Step 2: Discover available data sources
        available_files = self._discover_csv_files(job)
        api_fillable_range = self._calculate_api_range(job)

        # Step 3: Create ingestion plan
        plan = self._create_ingestion_plan(
            job=job,
            available_files=available_files,
            api_range=api_fillable_range
        )

        # Step 4: Execute CSV ingestion
        self._execute_csv_ingestion(job, plan.csv_files)

        # Step 5: Detect gaps
        gaps = self._detect_gaps(job)

        # Step 6: Backfill fillable gaps via API
        if job.api_backfill_enabled:
            self._backfill_gaps_via_api(job, gaps)

        # Step 7: Update coverage ranges
        self._update_coverage_ranges(job)

        # Step 8: Report completeness
        report = self._generate_completeness_report(job)
        self._display_report(report)

        # Step 9: Export unfillable gap recommendations
        if gaps.unfillable:
            self._export_csv_download_list(job, gaps.unfillable)
```

#### 3. Intelligent Data Source Router

**Purpose:** Decide whether to use CSV or API for each asset/interval/date-range

```python
class DataSourceRouter:
    """
    Route data ingestion to appropriate source (CSV vs API)
    based on date ranges and availability
    """

    def __init__(self, tier: str, intervals: List[int]):
        self.tier = tier
        self.intervals = intervals
        self.api_limit = 720  # Kraken API candle limit

    def create_ingestion_plan(
        self,
        start_date: datetime,
        end_date: datetime,
        available_csv_files: List[str]
    ) -> IngestionPlan:
        """
        Create a plan that routes data to appropriate sources

        Logic:
        1. For each asset/interval:
           a. Calculate date range that's API-fillable (last 720 candles)
           b. Check if CSV files exist for historical data (>720 candles ago)
           c. Route old data → CSV, recent data → API

        2. For gaps:
           a. Recent gaps (<720 candles) → API
           b. Historical gaps (>720 candles) → Flag for CSV download
        """
        plan = IngestionPlan()

        for asset in self._get_tier_assets(self.tier):
            for interval in self.intervals:
                # Calculate API-fillable range
                api_cutoff = self._calculate_api_cutoff_date(
                    interval_minutes=interval,
                    candle_limit=self.api_limit
                )

                # Historical data (before API cutoff)
                if start_date < api_cutoff:
                    csv_files = self._find_csv_files(
                        asset=asset,
                        interval=interval,
                        files=available_csv_files
                    )

                    if csv_files:
                        plan.add_csv_source(
                            asset=asset,
                            interval=interval,
                            files=csv_files,
                            date_range=(start_date, api_cutoff)
                        )
                    else:
                        plan.add_missing_csv(
                            asset=asset,
                            interval=interval,
                            date_range=(start_date, api_cutoff),
                            reason="Historical data beyond API limit"
                        )

                # Recent data (within API limit)
                if end_date >= api_cutoff:
                    plan.add_api_source(
                        asset=asset,
                        interval=interval,
                        date_range=(api_cutoff, end_date)
                    )

        return plan

    def _calculate_api_cutoff_date(
        self,
        interval_minutes: int,
        candle_limit: int
    ) -> datetime:
        """
        Calculate how far back the API can fetch

        Examples:
        - 1440 min (daily): 720 candles = ~2 years
        - 60 min (hourly): 720 candles = 30 days
        - 5 min: 720 candles = 2.5 days
        """
        minutes_back = interval_minutes * candle_limit
        return datetime.now() - timedelta(minutes=minutes_back)
```

#### 4. Integrated Gap Detection

**Purpose:** Detect gaps during ingestion, not as separate step

```python
class IntegratedGapDetector:
    """
    Detect gaps as coverage ranges are updated
    """

    def detect_gaps_for_asset(
        self,
        asset: Asset,
        interval_minutes: int,
        expected_start: datetime,
        expected_end: datetime
    ) -> List[Gap]:
        """
        Detect gaps by comparing expected vs actual coverage

        Steps:
        1. Query DataCoverageRange for this asset/interval
        2. Find missing date ranges
        3. Calculate candles_from_today for each gap
        4. Classify as API-fillable or not
        """
        coverage_ranges = DataCoverageRange.objects.filter(
            asset=asset,
            interval_minutes=interval_minutes,
            start_date__gte=expected_start,
            end_date__lte=expected_end
        ).order_by('start_date')

        gaps = []
        current_date = expected_start

        for coverage in coverage_ranges:
            if coverage.start_date > current_date:
                # Gap found
                gap = self._create_gap_record(
                    asset=asset,
                    interval_minutes=interval_minutes,
                    start=current_date,
                    end=coverage.start_date,
                    now=datetime.now()
                )
                gaps.append(gap)

            current_date = max(current_date, coverage.end_date)

        # Final gap (if coverage doesn't reach end)
        if current_date < expected_end:
            gap = self._create_gap_record(
                asset=asset,
                interval_minutes=interval_minutes,
                start=current_date,
                end=expected_end,
                now=datetime.now()
            )
            gaps.append(gap)

        return gaps

    def _create_gap_record(
        self,
        asset: Asset,
        interval_minutes: int,
        start: datetime,
        end: datetime,
        now: datetime
    ) -> GapRecord:
        """
        Create a gap record with API-fillability classification
        """
        missing_candles = int((end - start).total_seconds() / (interval_minutes * 60))
        candles_from_today = int((now - start).total_seconds() / (interval_minutes * 60))

        is_api_fillable = candles_from_today <= 720
        overflow_candles = max(0, candles_from_today - 720)

        gap = GapRecord.objects.create(
            asset=asset,
            interval_minutes=interval_minutes,
            gap_start=start,
            gap_end=end,
            missing_candles=missing_candles,
            is_api_fillable=is_api_fillable,
            overflow_candles=overflow_candles,
            status='DETECTED'
        )

        if not is_api_fillable:
            # Suggest CSV file to download
            gap.required_csv_file = self._suggest_csv_filename(
                asset=asset,
                interval_minutes=interval_minutes,
                start_date=start,
                end_date=end
            )
            gap.status = 'UNFILLABLE'
            gap.save()

        return gap
```

#### 5. Completeness Metrics & Reporting

**Purpose:** Answer "Do I have complete TIER1 data?"

```python
class CompletenessReporter:
    """
    Generate completeness reports for tiers
    """

    def generate_report(
        self,
        tier: str,
        intervals: List[int],
        start_date: datetime,
        end_date: datetime
    ) -> CompletenessReport:
        """
        Generate a comprehensive completeness report

        Metrics:
        - % of assets with complete data
        - % of expected records present
        - List of assets with gaps
        - List of unfillable gaps (require CSV download)
        """
        assets = Asset.objects.filter(
            tier=tier,
            category=Asset.Category.CRYPTO,
            active=True
        )

        report = CompletenessReport(
            tier=tier,
            intervals=intervals,
            date_range=(start_date, end_date)
        )

        for asset in assets:
            for interval in intervals:
                # Calculate expected candles
                expected_candles = self._calculate_expected_candles(
                    start_date=start_date,
                    end_date=end_date,
                    interval_minutes=interval
                )

                # Query actual records from QuestDB
                actual_candles = self._count_actual_candles(
                    asset=asset,
                    interval=interval,
                    start_date=start_date,
                    end_date=end_date
                )

                completeness_pct = (actual_candles / expected_candles) * 100

                report.add_asset_completeness(
                    asset=asset,
                    interval=interval,
                    expected=expected_candles,
                    actual=actual_candles,
                    completeness_pct=completeness_pct
                )

                # Find gaps
                gaps = GapRecord.objects.filter(
                    asset=asset,
                    interval_minutes=interval,
                    gap_start__gte=start_date,
                    gap_end__lte=end_date
                )

                for gap in gaps:
                    report.add_gap(gap)

        return report

    def display_report(self, report: CompletenessReport):
        """
        Display formatted completeness report

        Output format:

        ╔══════════════════════════════════════════════════════════╗
        ║  TIER1 Data Completeness Report                          ║
        ║  Date Range: 2020-01-01 to 2024-12-31                   ║
        ║  Intervals: 60min, 1440min                              ║
        ╚══════════════════════════════════════════════════════════╝

        Overall Statistics:
        • Total Assets: 20
        • Complete Assets: 18 (90%)
        • Partial Assets: 2 (10%)
        • Assets with Gaps: 2

        Interval Breakdown:

        60min (Hourly):
        • Average Completeness: 95.2%
        • Complete Assets: 19/20
        • Total Gaps: 3
          - API-Fillable: 2
          - Require CSV: 1

        1440min (Daily):
        • Average Completeness: 98.7%
        • Complete Assets: 20/20
        • Total Gaps: 0

        Assets Requiring Attention:

        1. XBTUSD (BTC/USD)
           60min: 92.3% complete
           Gap: 2023-06-15 to 2023-06-18 (72 candles)
           → API Fillable: Yes
           → Action: Run backfill_gaps command

        2. ETHUSD (ETH/USD)
           60min: 88.1% complete
           Gap: 2021-01-01 to 2021-03-31 (2,160 candles)
           → API Fillable: No (beyond 720-candle limit)
           → Action: Download CSV from Kraken
           → Suggested file: ETHUSD_60_2021Q1.csv

        Recommended Actions:

        1. Backfill 2 API-fillable gaps:
           python manage.py backfill_kraken_gaps --tier TIER1 --only-fillable

        2. Download 1 CSV file for unfillable gaps:
           • ETHUSD_60_2021Q1.csv

        3. Re-run ingestion after CSV download:
           python manage.py ingest_kraken_unified --tier TIER1
        """
        pass
```

---

## Implementation Plan

### Phase 1: Database Models (1-2 days)

1. Create migration for new models:
   - `IngestionJob`
   - `FileIngestionRecord`
   - `DataCoverageRange`
   - `GapRecord`

2. Add indexes and constraints

3. Create factory fixtures for testing

### Phase 2: Core Services (2-3 days)

1. **DataSourceRouter**
   - API cutoff date calculation
   - CSV file discovery
   - Ingestion plan creation

2. **IntegratedGapDetector**
   - Coverage range analysis
   - Gap detection logic
   - API-fillability classification

3. **CompletenessReporter**
   - Metrics calculation
   - Report generation
   - Terminal display formatting

### Phase 3: Unified Command (2-3 days)

1. **Command Structure**
   - Argument parsing
   - Job initialization/resumption
   - Workflow orchestration

2. **CSV Ingestion Integration**
   - Reuse existing `SequentialIngestor`
   - Add state tracking hooks
   - Update `FileIngestionRecord` after each file

3. **API Backfill Integration**
   - Reuse existing `GapBackfiller`
   - Route only API-fillable gaps
   - Update `GapRecord` status

### Phase 4: Coverage Tracking (1-2 days)

1. **Post-Ingestion Hook**
   - Calculate date ranges from ingested data
   - Update `DataCoverageRange` records
   - Merge overlapping ranges

2. **Gap Detection Trigger**
   - Detect gaps after coverage updates
   - Create `GapRecord` entries
   - Classify API-fillability

### Phase 5: Reporting & UX (1-2 days)

1. **Completeness Report**
   - Terminal-formatted output
   - CSV export option
   - JSON API endpoint (optional)

2. **Progress Display**
   - Real-time progress bars
   - ETA calculations
   - Current file/asset indicators

### Phase 6: Testing & Documentation (2-3 days)

1. **Unit Tests**
   - Test each service independently
   - Mock QuestDB queries
   - Test gap detection logic

2. **Integration Tests**
   - Test full workflow end-to-end
   - Test resumption from failures
   - Test incremental updates

3. **Documentation**
   - Update `ohlcv-ingestion.md`
   - Add usage examples
   - Add troubleshooting guide

---

## Migration Strategy

### Step 1: Parallel Implementation

Keep existing commands functional while building new system:
- `ingest_sequential` → Continue to work
- `backfill_kraken_gaps` → Continue to work
- `ingest_kraken_unified` → New command (doesn't interfere)

### Step 2: Gradual Adoption

1. Test new command on TIER4 (smallest tier)
2. Compare results with old workflow
3. Validate completeness metrics
4. Expand to TIER3, TIER2, TIER1

### Step 3: Deprecation

Once validated:
1. Add deprecation warnings to old commands
2. Update documentation to recommend new command
3. Remove old commands in next major version

---

## Usage Examples

### Complete TIER1 Ingestion (Fresh Start)

```bash
# Step 1: Download quarterly CSV files from Kraken
# (Manual step - download TIER1 pairs for all quarters)

# Step 2: Run unified ingestion
python manage.py ingest_kraken_unified \
    --tier TIER1 \
    --intervals 60,1440 \
    --start-date 2020-01-01 \
    --end-date 2024-12-31 \
    --complete \
    --yes

# Output:
# ╔══════════════════════════════════════════════════════════╗
# ║  Unified Kraken Ingestion - TIER1                        ║
# ╚══════════════════════════════════════════════════════════╝
#
# Job ID: a1b2c3d4-e5f6-7890-abcd-ef1234567890
#
# Step 1: Discovering data sources...
# ✓ Found 40 CSV files for 20 assets
# ✓ API available for last 720 candles
#
# Step 2: Creating ingestion plan...
# ✓ CSV ingestion: 2020-01-01 to 2022-12-31 (40 files)
# ✓ API backfill: 2023-01-01 to 2024-12-31 (20 assets)
#
# Step 3: Ingesting CSV files...
# [████████████████████████████████████████] 40/40 files
# ✓ Ingested 12,345,678 records
#
# Step 4: Detecting gaps...
# ✓ Found 3 gaps (2 API-fillable, 1 unfillable)
#
# Step 5: Backfilling via API...
# [████████████████████████████████████████] 2/2 gaps
# ✓ Filled 1,440 candles
#
# Step 6: Generating completeness report...
#
# ╔══════════════════════════════════════════════════════════╗
# ║  TIER1 Completeness Report                               ║
# ╚══════════════════════════════════════════════════════════╝
#
# Overall: 95.2% complete
# • 60min: 18/20 assets complete (90%)
# • 1440min: 20/20 assets complete (100%)
#
# Unfillable Gaps (require CSV download):
# 1. ETHUSD 60min: 2021-06-01 to 2021-06-30
#    → Download: ETHUSD_60_2021Q2.csv
#
# Next Steps:
# 1. Download missing CSV files
# 2. Re-run: python manage.py ingest_kraken_unified --resume a1b2c3d4
```

### Incremental Update (Daily Scheduled Run)

```bash
# Run via cron every day at 2 AM
0 2 * * * cd /app && python manage.py ingest_kraken_unified \
    --tier TIER1 \
    --intervals 60,1440 \
    --incremental \
    --yes

# Output:
# ╔══════════════════════════════════════════════════════════╗
# ║  Incremental Update - TIER1                              ║
# ╚══════════════════════════════════════════════════════════╝
#
# Last data point: 2024-12-30 23:00:00
# Fetching: 2024-12-30 23:00:00 to 2024-12-31 23:59:59
#
# [████████████████████████████████████████] 20/20 assets
# ✓ Updated with 480 new candles (60min)
# ✓ Updated with 20 new candles (1440min)
#
# Status: TIER1 remains 95.2% complete
```

### Resume Interrupted Job

```bash
# If ingestion was interrupted (Ctrl+C, system crash, etc.)
python manage.py ingest_kraken_unified --resume a1b2c3d4-e5f6-7890-abcd-ef1234567890

# Output:
# ╔══════════════════════════════════════════════════════════╗
# ║  Resuming Job: a1b2c3d4                                  ║
# ╚══════════════════════════════════════════════════════════╝
#
# Previous progress:
# • CSV files: 25/40 completed
# • Records ingested: 7,890,123
#
# Resuming CSV ingestion...
# [████████████████░░░░░░░░░░░░░░░░░░░░░░░] 25/40 files
```

---

## Benefits Summary

### 1. Single Source of Truth
- One command for all ingestion needs
- Clear state tracking in database
- Resumable workflows

### 2. Intelligent Routing
- Automatic CSV vs API selection
- Optimized for Kraken's 720-candle limit
- No wasted API calls on old data

### 3. Proactive Gap Management
- Gaps detected during ingestion
- Immediate backfill of API-fillable gaps
- Clear recommendations for CSV downloads

### 4. Tier-Based Completeness
- Answer "Is TIER1 complete?" instantly
- Track progress toward completeness goals
- Identify specific missing data ranges

### 5. Production Ready
- Resumable jobs (handle interruptions)
- Incremental updates (scheduled runs)
- State tracking (audit trail)
- Error handling (retry logic)

---

## Future Enhancements

### V2: Automated CSV Downloads
- Integrate with Kraken's export API (if available)
- Automatically download quarterly files
- Schedule quarterly updates

### V3: Multi-Exchange Support
- Extend architecture to support Binance, Coinbase, etc.
- Unified data model across exchanges
- Exchange-specific routers

### V4: Real-Time Streaming
- WebSocket integration for live data
- Continuous ingestion mode
- Sub-minute intervals (1min, 5min)

### V5: Data Quality Metrics
- Detect price anomalies
- Validate trade volumes
- Flag suspicious gaps (exchange outages)

---

## Comparison: Old vs New

| Feature | Old Workflow | New Unified Workflow |
|---------|-------------|----------------------|
| **Commands** | 3 separate commands | 1 unified command |
| **State Tracking** | None (stateless) | Database-backed state |
| **Resumability** | No (start over) | Yes (resume from failure) |
| **Gap Detection** | After ingestion | During ingestion |
| **API Routing** | Manual decision | Automatic based on date |
| **Completeness** | Manual queries | Built-in reports |
| **File Management** | Manual moves | Automatic tracking |
| **Incremental Updates** | Not supported | Built-in via `--incremental` |
| **Dry-Run** | No | Yes via `--dry-run` |
| **Progress Visibility** | Per-file only | Job-level + file-level |

---

## Conclusion

The unified Kraken ingestion architecture addresses all major pain points of the current 3-step process:

1. ✅ **Single coordinated workflow** replaces disconnected steps
2. ✅ **Persistent state tracking** enables resumability and progress monitoring
3. ✅ **Intelligent routing** optimizes CSV vs API based on 720-candle limit
4. ✅ **Integrated gap detection** catches issues early
5. ✅ **Tier-based completeness** provides clear visibility into data quality

This design is production-ready, extensible, and maintainable. The implementation plan breaks the work into manageable phases (~10-15 days total), with clear migration path from existing commands.
