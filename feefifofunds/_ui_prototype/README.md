# FeeFiFoFunds UI Prototype Files

**Status:** 🚧 ARCHIVED - NOT CURRENTLY FUNCTIONAL

This directory contains prototype/reference files for future UI development of the FeeFiFoFunds web interface.

## Important Notes

### These files are NOT currently functional because:

1. **Model Mismatch**: All templates reference models that don't exist in the current codebase:
   - Templates expect: `Fund`, `FundMetrics`, `FundPerformance`
   - Actual models: `Asset`, `AssetPrice`

2. **No Views**: There are no Django views to render these templates

3. **No URL Routes**: The `urls.py` file has empty `urlpatterns = []`

4. **Field Mismatches**: Templates reference fields that don't exist on current models:
   - `fund.slug`, `fund.ticker`, `fund.expense_ratio`, `fund.current_price`
   - `fund.get_fund_type_display()`, `fund.get_asset_class_display()`
   - `fund.issuer`, `fund.inception_date`, `fund.aum`, `fund.management_fee`

## Current FeeFiFoFunds Architecture

The current implementation is a **backend-only data tracking system**:

- **Models**: `Asset` (metadata) and `AssetPrice` (time-series data in QuestDB)
- **Purpose**: Multi-asset price tracking with high-throughput ingestion
- **Storage**: PostgreSQL + QuestDB hybrid architecture
- **Interface**: Management commands only (no web UI)

## What's Archived Here

### Templates (`templates/feefifofunds/`)
- `base.html` - Base template with navigation
- `home.html` - Dashboard with fund cards
- `fund_list.html` - Filterable fund listing
- `fund_detail.html` - Individual fund details with charts
- `compare.html` - Side-by-side fund comparison

### Static Files (`static/feefifofunds/`)
- `css/main.css` - Complete design system (350 lines)
- `js/main.js` - Mobile menu and smooth scroll (25 lines)

## Future Development

When building the web UI, these files serve as:

1. **Design Reference**: CSS provides a complete design system with color scheme, typography, and component styles
2. **Layout Reference**: Templates show the intended page structure and user flows
3. **Feature Ideas**: Templates demonstrate intended features (comparison, filtering, metrics display)

### To Make These Functional

1. **Option A - Adapt to Current Models**:
   - Rewrite templates to use `Asset` and `AssetPrice` models
   - Create views and URL routes
   - Build API endpoints for QuestDB time-series data

2. **Option B - Implement Original Design**:
   - Create new `Fund`, `FundMetrics`, `FundPerformance` models
   - Implement data aggregation layer from `AssetPrice` to `FundMetrics`
   - Migrate existing data structure

## History

These files were created as part of an initial design/prototype for a fund comparison and analysis platform. The project pivoted to focus on high-throughput data ingestion and backend tracking, making these UI files obsolete but potentially valuable for future development.

---

**Archived:** 2025-01-12
**Reason:** Dead code cleanup - no views/URLs to serve these templates, references non-existent models
**Decision:** Keep as reference for future UI development
