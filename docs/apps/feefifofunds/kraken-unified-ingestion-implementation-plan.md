# Kraken Unified Ingestion - Implementation Plan

## Overview

This document outlines the implementation plan for the unified Kraken data ingestion system. The new architecture replaces the current 3-step process with a single, stateful, tier-aware pipeline.

---

## ✅ Completed Work

### 1. Architecture Design (docs/apps/feefifofunds/kraken-unified-ingestion-architecture.md)

**Document includes:**
- Complete problem analysis of current system
- Detailed unified architecture design
- Database models specification
- Core services design (DataSourceRouter, IntegratedGapDetector, CompletenessReporter)
- Usage examples and migration strategy
- Benefits summary and future enhancements

### 2. Database Models (feefifofunds/models/ingestion.py)

**Created 4 new models:**

1. **IngestionJob** - Tracks high-level ingestion sessions
   - Job configuration (tier, intervals, date range)
   - Status tracking (PENDING, RUNNING, COMPLETED, FAILED, PAUSED)
   - Metrics (files processed, records ingested, gaps detected)
   - Error tracking

2. **FileIngestionRecord** - Tracks individual CSV files
   - File identification (path, hash for deduplication)
   - Asset/interval association
   - Status tracking
   - Date range and record count
   - Resumability support

3. **DataCoverageRange** - Tracks continuous data coverage
   - Asset/interval coverage ranges
   - Source tracking (CSV, API, MIXED)
   - Used for gap detection
   - Merge overlapping ranges support

4. **GapRecord** - Tracks detected gaps and backfill attempts
   - Gap date range and candle count
   - API fillability classification (720-candle limit)
   - Status tracking (DETECTED, BACKFILLING, FILLED, UNFILLABLE, FAILED)
   - CSV download recommendations for unfillable gaps

**Key Features:**
- All models have proper indexes for query performance
- Database constraints ensure data integrity
- Helper methods for state transitions
- Timestamped for audit trails

### 3. Model Registration

Updated `feefifofunds/models/__init__.py` to export new models for Django.

---

## 📋 Next Steps

### Phase 1: Generate Migration (MANUAL STEP REQUIRED)

```bash
# Generate migration for new models
python manage.py makemigrations feefifofunds

# Review the generated migration
# Expected migration operations:
# - Create 4 new tables
# - Add indexes and constraints
# - No data migrations needed (fresh tables)

# Apply migration
python manage.py migrate feefifofunds
```

**Verification:**
```bash
# Verify tables exist in PostgreSQL
python manage.py dbshell
\dt feefifofunds_*

# Expected tables:
# - feefifofunds_ingestion_job
# - feefifofunds_file_ingestion_record
# - feefifofunds_data_coverage_range
# - feefifofunds_gap_record
```

### Phase 2: Core Services Implementation

#### 2.1 DataSourceRouter Service
**File:** `feefifofunds/services/data_source_router.py`

**Purpose:** Route data ingestion to appropriate source (CSV vs API) based on date ranges.

**Key Methods:**
- `create_ingestion_plan()` - Analyze available sources and create execution plan
- `_calculate_api_cutoff_date()` - Calculate how far back API can fetch (720 candles)
- `_find_csv_files()` - Match CSV files to assets/intervals
- `_get_tier_assets()` - Get all assets for a tier

**Dependencies:**
- Existing: `feefifofunds.services.kraken` (tier definitions, pair parser)
- New: `IngestionJob`, `Asset`

**Estimated Time:** 1 day

#### 2.2 IntegratedGapDetector Service
**File:** `feefifofunds/services/gap_detector.py`

**Purpose:** Detect gaps by comparing expected vs actual coverage.

**Key Methods:**
- `detect_gaps_for_asset()` - Find missing date ranges for asset/interval
- `_create_gap_record()` - Create GapRecord with API-fillability
- `_query_coverage_ranges()` - Query DataCoverageRange
- `_suggest_csv_filename()` - Generate CSV download recommendations

**Dependencies:**
- New: `DataCoverageRange`, `GapRecord`, `Asset`
- Reuse: Logic from `backfill_kraken_gaps.py` (GapDetector, GapClassifier)

**Estimated Time:** 1-2 days

#### 2.3 CompletenessReporter Service
**File:** `feefifofunds/services/completeness_reporter.py`

**Purpose:** Generate tier-based completeness reports.

**Key Methods:**
- `generate_report()` - Create CompletenessReport for tier
- `_calculate_expected_candles()` - Calculate expected records
- `_count_actual_candles()` - Query QuestDB for actual records
- `display_report()` - Format terminal output with colors/tables

**Dependencies:**
- New: `DataCoverageRange`, `GapRecord`, `Asset`
- Existing: QuestDB client from `sequential_ingestor.py`

**Estimated Time:** 1 day

#### 2.4 CoverageTracker Service
**File:** `feefifofunds/services/coverage_tracker.py`

**Purpose:** Update DataCoverageRange after ingestion.

**Key Methods:**
- `update_coverage_after_ingestion()` - Create/update coverage ranges
- `_query_ingested_date_ranges()` - Query QuestDB for actual data
- `_merge_overlapping_ranges()` - Consolidate adjacent ranges
- `_calculate_record_count()` - Count records in range

**Dependencies:**
- New: `DataCoverageRange`, `FileIngestionRecord`, `Asset`
- Existing: QuestDB client

**Estimated Time:** 1 day

### Phase 3: Unified Command Implementation

#### 3.1 Management Command
**File:** `feefifofunds/management/commands/ingest_kraken_unified.py`

**Command Options:**
```python
# Required (one of)
--tier TIER1  # Specific tier
--tiers TIER1,TIER2  # Multiple tiers

# Date range
--start-date YYYY-MM-DD  # Default: 5 years ago
--end-date YYYY-MM-DD  # Default: today
--incremental  # From last data point to now

# Intervals
--intervals 60,1440  # Comma-separated, default: all

# Behavior
--complete  # Aim for 100% completeness
--resume JOB_UUID  # Resume interrupted job
--dry-run  # Show plan without executing
--yes  # Auto-confirm

# Options
--api-backfill / --no-api-backfill  # Enable/disable API backfill (default: enabled)
--auto-gap-fill / --no-auto-gap-fill  # Auto-fill gaps (default: enabled)
--csv-source-dir PATH  # Override CSV directory
```

**Workflow:**
```python
def handle(self, *args, **options):
    # 1. Initialize or resume job
    job = self._initialize_or_resume_job(options)

    # 2. Discover available data sources
    csv_files = self._discover_csv_files(job)
    api_range = self._calculate_api_range(job)

    # 3. Create ingestion plan
    router = DataSourceRouter(job.tier, job.intervals)
    plan = router.create_ingestion_plan(
        start_date=job.start_date,
        end_date=job.end_date,
        available_csv_files=csv_files
    )

    # 4. Display plan and confirm (if not --yes)
    if not options['yes']:
        self._display_plan(plan)
        if not self._confirm():
            return

    # 5. Execute CSV ingestion
    self._execute_csv_ingestion(job, plan.csv_files)

    # 6. Update coverage ranges
    tracker = CoverageTracker()
    tracker.update_coverage_after_ingestion(job)

    # 7. Detect gaps
    detector = IntegratedGapDetector()
    gaps = detector.detect_gaps_for_job(job)

    # 8. Backfill fillable gaps via API (if enabled)
    if job.api_backfill_enabled:
        self._backfill_gaps_via_api(job, gaps.fillable)

    # 9. Generate completeness report
    reporter = CompletenessReporter()
    report = reporter.generate_report(
        tier=job.tier,
        intervals=job.intervals,
        start_date=job.start_date,
        end_date=job.end_date
    )
    reporter.display_report(report)

    # 10. Export unfillable gap recommendations
    if gaps.unfillable:
        self._export_csv_download_list(job, gaps.unfillable)

    # 11. Mark job complete
    job.mark_completed()
```

**Key Implementation Details:**

1. **Resumability:**
   - Check for PAUSED/FAILED jobs with same config
   - Skip FileIngestionRecords with status=COMPLETED
   - Resume from last file

2. **CSV Ingestion:**
   - Reuse existing `SequentialIngestor` from `sequential_ingestor.py`
   - Wrap with `FileIngestionRecord` state tracking
   - Update job metrics after each file

3. **API Backfilling:**
   - Reuse existing `GapBackfiller` from `backfill_kraken_gaps.py`
   - Only backfill gaps with `is_api_fillable=True`
   - Update `GapRecord` status after each gap

4. **Progress Display:**
   - Reuse `ProgressReporter` from `progress_reporter.py`
   - Show overall job progress
   - Show current file progress
   - Calculate ETA

**Estimated Time:** 2-3 days

### Phase 4: Testing

#### 4.1 Unit Tests
**File:** `feefifofunds/tests/test_unified_ingestion.py`

**Test Cases:**
- Model methods (state transitions, fillability calculations)
- DataSourceRouter logic (API cutoff calculation, plan generation)
- IntegratedGapDetector (gap finding, fillability classification)
- CompletenessReporter (metrics calculation, report generation)
- CoverageTracker (range updates, merging)

**Estimated Time:** 1-2 days

#### 4.2 Integration Tests
**File:** `feefifofunds/tests/test_unified_ingestion_integration.py`

**Test Scenarios:**
- End-to-end ingestion (CSV → gaps → API → report)
- Job resumption after failure
- Incremental updates
- Multiple tiers
- Dry-run mode

**Estimated Time:** 1 day

### Phase 5: Documentation Updates

#### 5.1 Update ohlcv-ingestion.md
- Add "Unified Ingestion" section
- Update examples to use new command
- Add troubleshooting for new workflow
- Keep old command documentation with deprecation notes

#### 5.2 Add Migration Guide
- Create step-by-step migration from old to new workflow
- Include data validation steps
- Add rollback instructions

**Estimated Time:** 1 day

---

## 📊 Total Time Estimate

| Phase | Time Estimate |
|-------|--------------|
| Phase 1: Migration | 0.5 days |
| Phase 2: Core Services | 4-5 days |
| Phase 3: Unified Command | 2-3 days |
| Phase 4: Testing | 2-3 days |
| Phase 5: Documentation | 1 day |
| **Total** | **10-13 days** |

---

## 🔄 Suggested Implementation Order

1. **Week 1 (Days 1-5):**
   - Day 1: Run migration, create DataSourceRouter
   - Day 2: Create IntegratedGapDetector
   - Day 3: Create CompletenessReporter
   - Day 4: Create CoverageTracker
   - Day 5: Start unified command (basic structure)

2. **Week 2 (Days 6-10):**
   - Day 6-7: Complete unified command implementation
   - Day 8: Unit tests
   - Day 9: Integration tests
   - Day 10: Documentation updates

3. **Week 3 (Days 11-13):**
   - Day 11: Test on TIER4 (smallest tier)
   - Day 12: Test on TIER3, TIER2
   - Day 13: Test on TIER1, final validation

---

## 🚀 Quick Start (After Migration)

### Test on TIER4 First

```bash
# Generate and run migration
python manage.py makemigrations feefifofunds
python manage.py migrate feefifofunds

# Test unified ingestion on smallest tier (TIER4)
python manage.py ingest_kraken_unified \
    --tier TIER4 \
    --intervals 1440 \
    --start-date 2024-01-01 \
    --end-date 2024-12-31 \
    --dry-run

# If dry-run looks good, execute
python manage.py ingest_kraken_unified \
    --tier TIER4 \
    --intervals 1440 \
    --start-date 2024-01-01 \
    --end-date 2024-12-31 \
    --yes
```

### Validate Results

```bash
# Check IngestionJob
python manage.py shell
>>> from feefifofunds.models import IngestionJob
>>> job = IngestionJob.objects.last()
>>> print(f"Status: {job.status}")
>>> print(f"Progress: {job.progress_pct:.1f}%")
>>> print(f"Files: {job.files_ingested}/{job.total_files}")
>>> print(f"Records: {job.records_ingested:,}")
>>> print(f"Gaps: {job.gaps_detected} detected, {job.gaps_filled} filled")

# Check completeness in QuestDB
python manage.py dbshell --database questdb
SELECT asset_id, interval_minutes,
       COUNT(*) as records,
       MIN(time) as first_candle,
       MAX(time) as last_candle
FROM assetprice
WHERE asset_id IN (SELECT id FROM feefifofunds_asset WHERE tier='TIER4')
  AND interval_minutes = 1440
GROUP BY asset_id, interval_minutes
ORDER BY asset_id;
```

---

## 📁 File Structure Summary

```
feefifofunds/
├── models/
│   ├── __init__.py                 # ✅ Updated (exports new models)
│   ├── ingestion.py                # ✅ Created (4 new models)
│   ├── asset.py                    # Existing
│   └── price.py                    # Existing
│
├── services/
│   ├── sequential_ingestor.py     # Existing (will be reused)
│   ├── kraken.py                   # Existing (tier config, pair parser)
│   ├── data_source_router.py      # ⏳ To create
│   ├── gap_detector.py             # ⏳ To create
│   ├── completeness_reporter.py   # ⏳ To create
│   └── coverage_tracker.py         # ⏳ To create
│
├── management/commands/
│   ├── ingest_sequential.py        # Existing (will be deprecated)
│   ├── backfill_kraken_gaps.py    # Existing (will be deprecated)
│   └── ingest_kraken_unified.py   # ⏳ To create
│
└── tests/
    ├── test_unified_ingestion.py   # ⏳ To create
    └── test_unified_ingestion_integration.py  # ⏳ To create

docs/apps/feefifofunds/
├── kraken-unified-ingestion-architecture.md      # ✅ Created
├── kraken-unified-ingestion-implementation-plan.md  # ✅ Created (this file)
└── ohlcv-ingestion.md                            # ⏳ To update
```

---

## ⚠️ Important Notes

### Database Considerations

1. **PostgreSQL:**
   - 4 new tables for state tracking
   - Relatively small data volume (metadata only)
   - Normal Django migrations apply

2. **QuestDB:**
   - No changes to `assetprice` table
   - Continues to store OHLCV data
   - New queries for coverage range calculation

### Backward Compatibility

- Old commands (`ingest_sequential`, `backfill_kraken_gaps`) remain functional
- Can run old and new commands in parallel during transition
- New models don't interfere with existing data
- Migration path is reversible (can rollback)

### Performance

- State tracking adds minimal overhead (~0.1% of ingestion time)
- Coverage range queries are fast (indexed on asset/interval/date)
- Gap detection is now O(n) instead of O(n²) (integrated, not separate scan)
- Overall performance should be slightly better due to reduced redundancy

---

## 🎯 Success Criteria

The unified ingestion system will be considered successful when:

1. **Functional:**
   - ✅ Single command ingests complete tier data
   - ✅ Jobs are resumable after interruptions
   - ✅ Gaps are detected and classified correctly
   - ✅ API backfilling works for fillable gaps
   - ✅ Completeness reports are accurate

2. **Performance:**
   - ✅ Ingestion speed matches or exceeds current system (50K-100K rec/sec)
   - ✅ State tracking overhead < 1%
   - ✅ Gap detection completes in < 1 minute for TIER1

3. **Usability:**
   - ✅ Clear progress indicators
   - ✅ Helpful error messages
   - ✅ Actionable gap recommendations
   - ✅ Dry-run mode works correctly

4. **Reliability:**
   - ✅ No duplicate ingestion (hash-based deduplication)
   - ✅ Correct gap classification (API fillable vs unfillable)
   - ✅ Coverage ranges merge correctly
   - ✅ All tests pass

---

## 🔜 Next Action

**IMMEDIATE NEXT STEP:** Generate and apply the database migration.

```bash
# Generate migration
python manage.py makemigrations feefifofunds

# Review the migration file
cat feefifofunds/migrations/000X_add_ingestion_tracking.py

# Apply migration
python manage.py migrate feefifofunds

# Verify tables created
python manage.py dbshell
\dt feefifofunds_*
```

Once the migration is applied, proceed with Phase 2 (Core Services Implementation).
