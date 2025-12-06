"""
Data Source Router for intelligent CSV vs API routing.

This service determines the optimal data source (CSV files vs Kraken API)
for ingesting OHLCV data based on date ranges and the 720-candle API limit.
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import List

from feefifofunds.models import Asset
from feefifofunds.services.kraken import KrakenPairParser

logger = logging.getLogger(__name__)


@dataclass
class DataSource:
    """Represents a data source for an asset/interval."""

    asset: Asset
    interval_minutes: int
    date_range_start: datetime
    date_range_end: datetime
    source_type: str  # 'CSV' or 'API'
    csv_files: List[str] = field(default_factory=list)


@dataclass
class IngestionPlan:
    """Complete plan for ingesting data from multiple sources."""

    csv_sources: List[DataSource] = field(default_factory=list)
    api_sources: List[DataSource] = field(default_factory=list)
    missing_csv_sources: List[dict] = field(default_factory=list)

    @property
    def total_sources(self) -> int:
        """Total number of data sources."""
        return len(self.csv_sources) + len(self.api_sources)

    @property
    def has_missing_csv(self) -> bool:
        """Check if any CSV files are missing."""
        return len(self.missing_csv_sources) > 0

    def add_csv_source(self, asset: Asset, interval: int, files: List[str], date_range: tuple[datetime, datetime]):
        """Add a CSV data source to the plan."""
        self.csv_sources.append(
            DataSource(
                asset=asset,
                interval_minutes=interval,
                date_range_start=date_range[0],
                date_range_end=date_range[1],
                source_type="CSV",
                csv_files=files,
            )
        )

    def add_api_source(self, asset: Asset, interval: int, date_range: tuple[datetime, datetime]):
        """Add an API data source to the plan."""
        self.api_sources.append(
            DataSource(
                asset=asset,
                interval_minutes=interval,
                date_range_start=date_range[0],
                date_range_end=date_range[1],
                source_type="API",
            )
        )

    def add_missing_csv(self, asset: Asset, interval: int, date_range: tuple[datetime, datetime], reason: str):
        """Record a missing CSV file that needs to be downloaded."""
        self.missing_csv_sources.append(
            {
                "asset": asset,
                "ticker": asset.ticker,
                "interval_minutes": interval,
                "date_range_start": date_range[0],
                "date_range_end": date_range[1],
                "reason": reason,
                "suggested_filename": f"{asset.ticker}USD_{interval}.csv",
            }
        )


class DataSourceRouter:
    """
    Intelligent router that determines optimal data source (CSV vs API)
    for each asset/interval based on date ranges and availability.

    Key Logic:
    - Historical data (>720 candles ago): Use CSV files
    - Recent data (≤720 candles): Use Kraken API
    - Missing CSV files: Flag for manual download
    """

    API_CANDLE_LIMIT = 720  # Kraken API maximum

    def __init__(
        self,
        tier: str,
        intervals: List[int],
        csv_source_dir: str | None = None,
    ):
        """
        Initialize router.

        Args:
            tier: Asset tier (TIER1, TIER2, TIER3, TIER4, or ALL)
            intervals: List of interval minutes to process
            csv_source_dir: Directory containing CSV files (default: from settings)
        """
        self.tier = tier
        self.intervals = intervals
        self.csv_source_dir = csv_source_dir or self._get_default_csv_dir()

        logger.info(f"DataSourceRouter initialized: tier={tier}, intervals={intervals}")

    def _get_default_csv_dir(self) -> str:
        """Get default CSV source directory."""
        # Default to the Kraken OHLCVT directory
        return str(Path(__file__).parent.parent / "data" / "kraken" / "Kraken_OHLCVT")

    def create_ingestion_plan(
        self,
        start_date: datetime,
        end_date: datetime,
        available_csv_files: List[str] | None = None,
    ) -> IngestionPlan:
        """
        Create a comprehensive ingestion plan routing data to appropriate sources.

        Logic:
        1. For each asset/interval:
           a. Calculate API-fillable date range (last 720 candles)
           b. Check if CSV files exist for historical data (>720 candles ago)
           c. Route: old data → CSV, recent data → API
           d. Flag missing CSV files for manual download

        Args:
            start_date: Ingestion start date
            end_date: Ingestion end date (default: now)
            available_csv_files: List of available CSV file paths (optional)

        Returns:
            IngestionPlan with CSV sources, API sources, and missing CSV list
        """
        logger.info(f"Creating ingestion plan: {start_date} to {end_date}")

        plan = IngestionPlan()

        # Discover available CSV files if not provided
        if available_csv_files is None:
            available_csv_files = self._discover_csv_files()

        logger.info(f"Found {len(available_csv_files)} CSV files in {self.csv_source_dir}")

        # Get assets for tier
        assets = self._get_tier_assets()
        logger.info(f"Processing {assets.count()} assets for tier {self.tier}")

        for asset in assets:
            for interval in self.intervals:
                # Calculate API cutoff date (how far back API can fetch)
                api_cutoff_date = self._calculate_api_cutoff_date(interval)

                logger.debug(
                    f"{asset.ticker} {interval}min: API cutoff={api_cutoff_date.date()}, "
                    f"start={start_date.date()}, end={end_date.date()}"
                )

                # Historical data (before API cutoff) - requires CSV
                if start_date < api_cutoff_date:
                    csv_files = self._find_csv_files_for_asset(
                        asset=asset, interval=interval, available_files=available_csv_files
                    )

                    if csv_files:
                        plan.add_csv_source(
                            asset=asset,
                            interval=interval,
                            files=csv_files,
                            date_range=(start_date, min(api_cutoff_date, end_date)),
                        )
                        logger.debug(f"  → CSV source: {len(csv_files)} files")
                    else:
                        # Missing CSV files for historical data
                        plan.add_missing_csv(
                            asset=asset,
                            interval=interval,
                            date_range=(start_date, min(api_cutoff_date, end_date)),
                            reason=f"Historical data beyond API limit ({self.API_CANDLE_LIMIT} candles)",
                        )
                        logger.warning(f"  → Missing CSV for historical data: {asset.ticker} {interval}min")

                # Recent data (within API limit) - use API
                if end_date >= api_cutoff_date:
                    plan.add_api_source(
                        asset=asset,
                        interval=interval,
                        date_range=(max(api_cutoff_date, start_date), end_date),
                    )
                    logger.debug(f"  → API source: {api_cutoff_date.date()} to {end_date.date()}")

        logger.info(
            f"Ingestion plan created: {len(plan.csv_sources)} CSV sources, "
            f"{len(plan.api_sources)} API sources, {len(plan.missing_csv_sources)} missing CSV files"
        )

        return plan

    def _calculate_api_cutoff_date(self, interval_minutes: int) -> datetime:
        """
        Calculate how far back the Kraken API can fetch data.

        Kraken API returns maximum 720 candles. Calculate the date
        that's 720 candles ago from now.

        Examples:
        - 1440 min (daily): 720 candles = ~2 years ago
        - 60 min (hourly): 720 candles = 30 days ago
        - 5 min: 720 candles = ~2.5 days ago

        Args:
            interval_minutes: Candle interval in minutes

        Returns:
            Datetime representing the API cutoff (oldest fetchable date)
        """
        minutes_back = interval_minutes * self.API_CANDLE_LIMIT
        cutoff = datetime.now() - timedelta(minutes=minutes_back)

        logger.debug(f"API cutoff for {interval_minutes}min: {cutoff.date()} ({self.API_CANDLE_LIMIT} candles back)")

        return cutoff

    def _get_tier_assets(self) -> list[Asset]:
        """
        Get all active crypto assets for the specified tier.

        Returns:
            QuerySet of Asset objects
        """
        if self.tier == "ALL":
            return Asset.objects.filter(category=Asset.Category.CRYPTO, active=True).order_by("ticker")
        else:
            return Asset.objects.filter(category=Asset.Category.CRYPTO, tier=self.tier, active=True).order_by("ticker")

    def _discover_csv_files(self) -> List[str]:
        """
        Discover all CSV files in the source directory.

        Returns:
            List of absolute file paths
        """
        csv_dir = Path(self.csv_source_dir)

        if not csv_dir.exists():
            logger.warning(f"CSV directory does not exist: {csv_dir}")
            return []

        csv_files = list(csv_dir.glob("*.csv"))
        logger.info(f"Discovered {len(csv_files)} CSV files in {csv_dir}")

        return [str(f) for f in csv_files]

    def _find_csv_files_for_asset(self, asset: Asset, interval: int, available_files: List[str]) -> List[str]:
        """
        Find CSV files matching a specific asset and interval.

        Expected filename format: {PAIR}_{INTERVAL}.csv
        Examples: XBTUSD_1440.csv, ETHUSD_60.csv

        Args:
            asset: Asset to find files for
            interval: Interval minutes
            available_files: List of available CSV file paths

        Returns:
            List of matching file paths
        """
        matching_files = []

        # Try multiple ticker variations (BTC vs XBT, etc.)
        ticker_variations = self._get_ticker_variations(asset.ticker)

        for file_path in available_files:
            filename = Path(file_path).name

            # Parse filename: {PAIR}_{INTERVAL}.csv
            if "_" not in filename:
                continue

            try:
                pair_part, interval_part = filename.rsplit("_", 1)
                interval_part = interval_part.replace(".csv", "")

                # Check if interval matches
                if int(interval_part) != interval:
                    continue

                # Check if pair matches any ticker variation
                # Parse the pair to extract base ticker
                try:
                    parser = KrakenPairParser(pair_part)
                    base_ticker = parser.get_base_ticker()

                    if base_ticker in ticker_variations:
                        matching_files.append(file_path)
                        logger.debug(f"    Matched: {filename} for {asset.ticker}")

                except ValueError as e:
                    logger.debug(f"    Skipped: {filename} - parsing error: {e}")
                    continue

            except (ValueError, IndexError) as e:
                logger.debug(f"    Skipped: {filename} - invalid format: {e}")
                continue

        return matching_files

    def _get_ticker_variations(self, ticker: str) -> List[str]:
        """
        Get ticker variations for matching (e.g., BTC → [BTC, XBT, XXBT]).

        Args:
            ticker: Base ticker symbol

        Returns:
            List of ticker variations
        """
        variations = [ticker]

        # Kraken-specific mappings
        kraken_mappings = {
            "BTC": ["XBT", "XXBT", "XBTC"],
            "DOGE": ["XDG", "XDGE"],
        }

        if ticker in kraken_mappings:
            variations.extend(kraken_mappings[ticker])

        # Reverse mappings
        for base, alts in kraken_mappings.items():
            if ticker in alts:
                variations.append(base)
                variations.extend(alts)

        return list(set(variations))  # Remove duplicates

    def get_plan_summary(self, plan: IngestionPlan) -> dict:
        """
        Generate a human-readable summary of the ingestion plan.

        Args:
            plan: IngestionPlan to summarize

        Returns:
            Dictionary with summary statistics
        """
        summary = {
            "total_sources": plan.total_sources,
            "csv_sources": len(plan.csv_sources),
            "api_sources": len(plan.api_sources),
            "missing_csv_files": len(plan.missing_csv_sources),
            "assets_by_source": {"csv_only": 0, "api_only": 0, "both": 0},
            "date_ranges": {
                "csv_earliest": None,
                "csv_latest": None,
                "api_earliest": None,
                "api_latest": None,
            },
        }

        # Calculate date ranges
        if plan.csv_sources:
            summary["date_ranges"]["csv_earliest"] = min(s.date_range_start for s in plan.csv_sources)
            summary["date_ranges"]["csv_latest"] = max(s.date_range_end for s in plan.csv_sources)

        if plan.api_sources:
            summary["date_ranges"]["api_earliest"] = min(s.date_range_start for s in plan.api_sources)
            summary["date_ranges"]["api_latest"] = max(s.date_range_end for s in plan.api_sources)

        # Count assets by source type
        csv_assets = {(s.asset.id, s.interval_minutes) for s in plan.csv_sources}
        api_assets = {(s.asset.id, s.interval_minutes) for s in plan.api_sources}

        summary["assets_by_source"]["csv_only"] = len(csv_assets - api_assets)
        summary["assets_by_source"]["api_only"] = len(api_assets - csv_assets)
        summary["assets_by_source"]["both"] = len(csv_assets & api_assets)

        return summary

    def display_plan(self, plan: IngestionPlan):
        """
        Display the ingestion plan in a human-readable format.

        Args:
            plan: IngestionPlan to display
        """
        summary = self.get_plan_summary(plan)

        print("\n╔══════════════════════════════════════════════════════════╗")
        print("║            Ingestion Plan Summary                        ║")
        print("╚══════════════════════════════════════════════════════════╝\n")

        print(f"Total Data Sources: {summary['total_sources']}")
        print(f"  • CSV sources: {summary['csv_sources']}")
        print(f"  • API sources: {summary['api_sources']}")
        print(f"  • Missing CSV files: {summary['missing_csv_files']}\n")

        if summary["date_ranges"]["csv_earliest"]:
            print(
                f"CSV Date Range: {summary['date_ranges']['csv_earliest'].date()} "
                f"to {summary['date_ranges']['csv_latest'].date()}"
            )

        if summary["date_ranges"]["api_earliest"]:
            print(
                f"API Date Range: {summary['date_ranges']['api_earliest'].date()} "
                f"to {summary['date_ranges']['api_latest'].date()}"
            )

        print("\nAssets by Source:")
        print(f"  • CSV only: {summary['assets_by_source']['csv_only']}")
        print(f"  • API only: {summary['assets_by_source']['api_only']}")
        print(f"  • Both CSV & API: {summary['assets_by_source']['both']}")

        if plan.missing_csv_sources:
            print(f"\n⚠️  Missing CSV Files ({len(plan.missing_csv_sources)}):")
            for missing in plan.missing_csv_sources[:5]:  # Show first 5
                print(f"  • {missing['ticker']} {missing['interval_minutes']}min: {missing['suggested_filename']}")
            if len(plan.missing_csv_sources) > 5:
                print(f"  ... and {len(plan.missing_csv_sources) - 5} more")

        print()
