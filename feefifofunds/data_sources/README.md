# Fund Data Sources

Multi-source data fetching system for populating fund data from various providers.

## Overview

This package provides a pluggable architecture for fetching fund data from multiple sources with automatic fallback, caching, and rate limiting.

## Architecture

```
data_sources/
├── __init__.py           # Package exports
├── base.py               # Abstract base class for all sources
├── dto.py                # FundDataDTO - standardized data structure
├── manager.py            # Orchestrates multiple sources
├── yahoo_finance.py      # Yahoo Finance source (ETFs)
├── alpha_vantage.py      # Alpha Vantage API source (ETFs)
└── csv_source.py         # CSV import source (all funds)
```

## Available Data Sources

### 1. Yahoo Finance (`yahoo_finance.py`)
- **Best For**: ETF data (Canadian `.TO` and US)
- **Cost**: Free, no API key required
- **Rate Limit**: Built-in (500ms delay)
- **Supports**: ETFs only
- **Library**: `yfinance`

**Pros**:
- Easy to use, no setup required
- Good coverage of Canadian and US ETFs
- Includes MER, performance data, and AUM

**Cons**:
- Limited mutual fund data
- No search functionality

### 2. Alpha Vantage (`alpha_vantage.py`)
- **Best For**: ETF fundamentals (US primarily)
- **Cost**: Free tier (500 req/day, 5 calls/min)
- **Rate Limit**: 5 calls/minute (12s delay enforced)
- **Supports**: ETFs only
- **API Key**: Required (get at https://www.alphavantage.co/support/#api-key)

**Pros**:
- Official API with good documentation
- Reliable data quality

**Cons**:
- Requires API key setup
- Limited Canadian fund coverage
- MER data not always available
- Rate limits on free tier

### 3. CSV Source (`csv_source.py`)
- **Best For**: Manual data entry, mutual funds
- **Cost**: Free (local files)
- **Rate Limit**: None
- **Supports**: Both ETFs and mutual funds

**Pros**:
- Complete control over data
- Supports mutual funds
- Great for bulk imports
- No API limits

**Cons**:
- Manual data entry required
- Data can become stale

## Installation

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. (Optional) Set up Alpha Vantage API key:
```bash
export ALPHA_VANTAGE_API_KEY="your_key_here"
```

## Usage

### Quick Start: Fetch a Single Fund

```bash
# Fetch from Yahoo Finance (ETF)
python manage.py fetch_fund VFV.TO

# Fetch multiple funds
python manage.py fetch_fund VFV.TO VGRO.TO XIC.TO

# Dry run (don't save to DB)
python manage.py fetch_fund VFV.TO --dry-run

# Use specific source
python manage.py fetch_fund VFV.TO --source yahoo
```

### Import from CSV

```bash
# Generate a sample CSV
python manage.py import_funds_csv --generate-sample sample_funds.csv

# Import funds from CSV
python manage.py import_funds_csv sample_funds.csv

# Dry run
python manage.py import_funds_csv funds.csv --dry-run
```

### Programmatic Usage

```python
from feefifofunds.data_sources import (
    DataSourceManager,
    YahooFinanceSource,
    AlphaVantageSource,
    CSVSource
)

# Setup manager with multiple sources (tries in order)
manager = DataSourceManager()
manager.add_source(YahooFinanceSource())  # Priority 0
manager.add_source(AlphaVantageSource(api_key="..."))  # Priority 1

# Fetch a fund (tries Yahoo first, then Alpha Vantage)
fund_data = manager.fetch_fund("VFV.TO")

if fund_data:
    print(f"Found: {fund_data.name}")
    print(f"MER: {fund_data.mer}%")

    # Save to database
    fund = manager.save_to_db(fund_data, update_existing=True)
    print(f"Saved to DB with ID: {fund.id}")
```

## CSV Format

The CSV source expects the following columns (only `ticker`, `name`, and `fund_type` are required):

### Required Columns
- `ticker` - Fund ticker symbol (e.g., VFV.TO, TDB902)
- `name` - Full fund name
- `fund_type` - Either "ETF" or "MUTUAL_FUND"

### Optional Columns
- `provider` - Provider name (e.g., Vanguard, TD)
- `mer` - Management Expense Ratio as percentage (e.g., 0.08)
- `asset_class` - EQUITY, BONDS, BALANCED, MONEY_MARKET, REAL_ESTATE, COMMODITIES, ALTERNATIVE
- `geographic_focus` - CANADIAN, US, INTERNATIONAL, GLOBAL, EMERGING, REGIONAL
- `description` - Fund description
- `ytd_return` - Year-to-date return (%)
- `one_year_return` - 1-year return (%)
- `three_year_return` - 3-year annualized return (%)
- `five_year_return` - 5-year annualized return (%)
- `ten_year_return` - 10-year annualized return (%)
- `inception_date` - Date in YYYY-MM-DD format
- `aum` - Assets under management in millions
- `minimum_investment` - Minimum investment amount
- `front_load` - Front-end load fee (%)
- `back_load` - Back-end load/DSC fee (%)
- `transaction_fee` - Transaction fee in dollars
- `data_source_url` - URL to fund's official page

### Example CSV

```csv
ticker,name,provider,fund_type,mer,asset_class,geographic_focus,description,one_year_return
VFV.TO,Vanguard S&P 500 Index ETF,Vanguard,ETF,0.08,EQUITY,US,"Tracks S&P 500",15.2
TDB902,TD U.S. Index Fund - e Series,TD,MUTUAL_FUND,0.35,EQUITY,US,"Low-cost index fund",14.8
RBF556,RBC Select Balanced Portfolio,RBC,MUTUAL_FUND,2.04,BALANCED,GLOBAL,"Actively managed",8.5
```

## Features

### Caching
All sources support Redis/file-based caching with configurable TTL (default: 24 hours).

```python
source = YahooFinanceSource(cache_timeout=43200, enable_cache=True)  # 12 hour cache
```

### Rate Limiting
Sources automatically enforce rate limits:
- Yahoo Finance: 500ms between requests
- Alpha Vantage: 12s between requests (5 per minute)
- CSV: No limits

### Data Merging
Fetch from multiple sources and merge results:

```python
fund_data = manager.fetch_fund(
    "VFV.TO",
    try_all_sources=True,
    merge_results=True
)
```

### Error Handling
Graceful degradation with fallback to next source on failure.

## Adding New Sources

To add a new data source:

1. Create a new file (e.g., `morningstar.py`)
2. Subclass `BaseDataSource`
3. Implement required methods:
   - `fetch_fund(ticker)` - Fetch single fund
   - `supports_fund_type(fund_type)` - Check if ETF/MUTUAL_FUND supported
4. Optional methods:
   - `fetch_multiple(tickers)` - Batch fetch
   - `search_funds(query)` - Search functionality
5. Return `FundDataDTO` objects

```python
from .base import BaseDataSource
from .dto import FundDataDTO

class MorningstarSource(BaseDataSource):
    def fetch_fund(self, ticker: str) -> Optional[FundDataDTO]:
        # Your implementation
        return FundDataDTO(
            ticker=ticker,
            name="Fund Name",
            fund_type="ETF",
            # ... other fields
        )

    def supports_fund_type(self, fund_type: str) -> bool:
        return fund_type in ["ETF", "MUTUAL_FUND"]
```

## Tips

### Recommended Source Priority

1. **For Canadian ETFs**: Yahoo Finance (best data coverage)
2. **For US ETFs**: Yahoo Finance or Alpha Vantage
3. **For Mutual Funds**: CSV import (manual entry)

### Getting Good MER Data

- Yahoo Finance usually has accurate MER for ETFs
- Alpha Vantage often missing MER data
- For mutual funds, use CSV import with data from fund fact sheets

### Batch Operations

Use ticker files for batch operations:

```bash
# Create ticker file
echo "VFV.TO
VGRO.TO
XIC.TO
VUN.TO" > canadian_etfs.txt

# Fetch all
python manage.py fetch_fund --file canadian_etfs.txt
```

## Troubleshooting

### "No data found"
- Check ticker format (Canadian ETFs need `.TO` suffix)
- Try a different source
- Verify the fund is publicly traded

### "yfinance library not installed"
```bash
pip install yfinance
```

### "Alpha Vantage API key required"
Get free key at: https://www.alphavantage.co/support/#api-key

Set environment variable:
```bash
export ALPHA_VANTAGE_API_KEY="your_key"
```

Or pass directly:
```bash
python manage.py fetch_fund VOO --source alpha_vantage --alpha-vantage-key "your_key"
```

### Rate Limiting Errors
- Alpha Vantage free tier: 5 calls/minute, 500/day
- Solution: Use CSV import for bulk data or upgrade API tier

## Future Enhancements

Potential additional sources:
- Morningstar scraper (Canadian mutual funds)
- SEDAR+ integration (official Canadian filings)
- TMX Money API (TSX-listed ETFs)
- Direct fund company APIs (Vanguard, iShares, etc.)
