"""
Data source manager for orchestrating multiple fund data sources with fallback logic.
"""

import logging
from typing import List, Optional

from django.db import transaction

from feefifofunds.models import Fund, FundProvider

from .base import BaseDataSource
from .dto import FundDataDTO

logger = logging.getLogger(__name__)


class DataSourceManager:
    """
    Manages multiple data sources with fallback and merge logic.

    Usage:
        manager = DataSourceManager()
        manager.add_source(YahooFinanceSource())
        manager.add_source(AlphaVantageSource(api_key="..."))

        fund_data = manager.fetch_fund("VFV.TO")
        fund = manager.save_to_db(fund_data)
    """

    def __init__(self):
        self.sources: List[BaseDataSource] = []

    def add_source(self, source: BaseDataSource, priority: Optional[int] = None):
        """
        Add a data source.

        Args:
            source: DataSource instance
            priority: Optional priority (lower = higher priority). If None, appends to end.
        """
        if priority is not None:
            self.sources.insert(priority, source)
        else:
            self.sources.append(source)

        logger.info(f"[Manager] Added source: {source.source_name}")

    def fetch_fund(
        self, ticker: str, try_all_sources: bool = False, merge_results: bool = False
    ) -> Optional[FundDataDTO]:
        """
        Fetch fund data from available sources with fallback.

        Args:
            ticker: Fund ticker
            try_all_sources: If True, try all sources even if first succeeds
            merge_results: If True and try_all_sources=True, merge data from multiple sources

        Returns:
            FundDataDTO if found, None otherwise
        """
        if not self.sources:
            logger.error("[Manager] No data sources configured")
            return None

        results = []

        for source in self.sources:
            try:
                logger.info(f"[Manager] Trying {source.source_name} for {ticker}")
                fund_data = source.fetch_fund(ticker)

                if fund_data:
                    logger.info(f"[Manager] Found {ticker} in {source.source_name}")
                    results.append(fund_data)

                    if not try_all_sources:
                        return fund_data
                else:
                    logger.debug(f"[Manager] {ticker} not found in {source.source_name}")

            except Exception as e:
                logger.error(f"[Manager] Error fetching from {source.source_name}: {e}")
                continue

        # If we tried all sources
        if results:
            if merge_results and len(results) > 1:
                logger.info(f"[Manager] Merging {len(results)} results for {ticker}")
                return self._merge_fund_data(results)
            else:
                return results[0]

        logger.warning(f"[Manager] No data found for {ticker} in any source")
        return None

    def _merge_fund_data(self, fund_data_list: List[FundDataDTO]) -> FundDataDTO:
        """
        Merge multiple FundDataDTO objects, preferring more complete data.

        Strategy:
        - Start with first result
        - Fill in missing fields from subsequent results
        - For conflicting data, prefer source with more complete info
        """
        if not fund_data_list:
            raise ValueError("Cannot merge empty list")

        if len(fund_data_list) == 1:
            return fund_data_list[0]

        # Start with first result
        merged = fund_data_list[0]

        # Merge with remaining results
        for fund_data in fund_data_list[1:]:
            merged = merged.merge_with(fund_data, prefer_other=False)

        logger.info(f"[Manager] Merged data from {len(fund_data_list)} sources")
        return merged

    def save_to_db(
        self, fund_data: FundDataDTO, update_existing: bool = True, create_provider: bool = True
    ) -> Optional[Fund]:
        """
        Save FundDataDTO to database.

        Args:
            fund_data: FundDataDTO to save
            update_existing: If True, update existing fund. If False, skip if exists.
            create_provider: If True, create FundProvider if doesn't exist

        Returns:
            Fund instance if saved, None if skipped

        Raises:
            ValueError: If fund_data is invalid
        """
        if not fund_data.is_complete():
            raise ValueError(f"Incomplete fund data for {fund_data.ticker}: missing required fields")

        with transaction.atomic():
            # Get or create provider
            provider = self._get_or_create_provider(fund_data.provider_name, create_provider)
            if not provider:
                raise ValueError(f"Provider '{fund_data.provider_name}' not found and create_provider=False")

            # Check if fund exists
            try:
                fund = Fund.objects.get(ticker=fund_data.ticker)

                if not update_existing:
                    logger.info(f"[Manager] Fund {fund_data.ticker} already exists, skipping (update_existing=False)")
                    return None

                logger.info(f"[Manager] Updating existing fund: {fund_data.ticker}")
                self._update_fund_from_dto(fund, fund_data, provider)

            except Fund.DoesNotExist:
                logger.info(f"[Manager] Creating new fund: {fund_data.ticker}")
                fund = self._create_fund_from_dto(fund_data, provider)

            fund.save()
            logger.info(f"[Manager] Saved fund: {fund.ticker} ({fund.name})")
            return fund

    def _get_or_create_provider(self, provider_name: Optional[str], create_if_missing: bool) -> Optional[FundProvider]:
        """Get or create FundProvider."""
        if not provider_name:
            provider_name = "Unknown"

        try:
            return FundProvider.objects.get(name=provider_name)
        except FundProvider.DoesNotExist:
            if create_if_missing:
                logger.info(f"[Manager] Creating provider: {provider_name}")
                provider = FundProvider(name=provider_name)
                provider.save()
                return provider
            else:
                return None

    def _create_fund_from_dto(self, fund_data: FundDataDTO, provider: FundProvider) -> Fund:
        """Create new Fund instance from FundDataDTO."""
        return Fund(
            ticker=fund_data.ticker,
            name=fund_data.name,
            provider=provider,
            fund_type=fund_data.fund_type,
            description=fund_data.description or "",
            mer=fund_data.mer,
            front_load=fund_data.front_load,
            back_load=fund_data.back_load,
            transaction_fee=fund_data.transaction_fee,
            asset_class=fund_data.asset_class,
            geographic_focus=fund_data.geographic_focus,
            ytd_return=fund_data.ytd_return,
            one_year_return=fund_data.one_year_return,
            three_year_return=fund_data.three_year_return,
            five_year_return=fund_data.five_year_return,
            ten_year_return=fund_data.ten_year_return,
            inception_date=fund_data.inception_date,
            aum=fund_data.aum,
            minimum_investment=fund_data.minimum_investment,
            last_data_update=fund_data.last_data_update,
            data_source_url=fund_data.data_source_url or "",
            is_active=fund_data.is_active,
        )

    def _update_fund_from_dto(self, fund: Fund, fund_data: FundDataDTO, provider: FundProvider):
        """Update existing Fund instance from FundDataDTO."""
        # Always update these fields
        fund.name = fund_data.name
        fund.provider = provider

        # Update optional fields only if they have values
        if fund_data.description:
            fund.description = fund_data.description
        if fund_data.mer is not None:
            fund.mer = fund_data.mer
        if fund_data.front_load is not None:
            fund.front_load = fund_data.front_load
        if fund_data.back_load is not None:
            fund.back_load = fund_data.back_load
        if fund_data.transaction_fee is not None:
            fund.transaction_fee = fund_data.transaction_fee
        if fund_data.asset_class:
            fund.asset_class = fund_data.asset_class
        if fund_data.geographic_focus:
            fund.geographic_focus = fund_data.geographic_focus

        # Update performance data
        if fund_data.ytd_return is not None:
            fund.ytd_return = fund_data.ytd_return
        if fund_data.one_year_return is not None:
            fund.one_year_return = fund_data.one_year_return
        if fund_data.three_year_return is not None:
            fund.three_year_return = fund_data.three_year_return
        if fund_data.five_year_return is not None:
            fund.five_year_return = fund_data.five_year_return
        if fund_data.ten_year_return is not None:
            fund.ten_year_return = fund_data.ten_year_return

        # Update fund details
        if fund_data.inception_date:
            fund.inception_date = fund_data.inception_date
        if fund_data.aum is not None:
            fund.aum = fund_data.aum
        if fund_data.minimum_investment is not None:
            fund.minimum_investment = fund_data.minimum_investment

        # Update metadata
        if fund_data.last_data_update:
            fund.last_data_update = fund_data.last_data_update
        if fund_data.data_source_url:
            fund.data_source_url = fund_data.data_source_url

        fund.is_active = fund_data.is_active

    def list_sources(self) -> List[dict]:
        """Get information about all configured sources."""
        return [source.get_source_info() for source in self.sources]

    def get_source_by_name(self, name: str) -> Optional[BaseDataSource]:
        """Get a source by name."""
        for source in self.sources:
            if source.source_name == name:
                return source
        return None

    def __repr__(self):
        source_names = [s.source_name for s in self.sources]
        return f"DataSourceManager(sources={source_names})"
