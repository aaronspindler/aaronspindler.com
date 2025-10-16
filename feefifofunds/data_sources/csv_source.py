"""
CSV file data source for manual fund data import.

Best for: Mutual funds and manual data entry
Free: Yes
Rate Limit: N/A (local file)
"""

import csv
import logging
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import List, Optional

from .base import BaseDataSource
from .dto import FundDataDTO

logger = logging.getLogger(__name__)


class CSVSource(BaseDataSource):
    """
    Import fund data from CSV files.

    CSV Format:
    ticker,name,provider,fund_type,mer,asset_class,geographic_focus,description,
    one_year_return,three_year_return,five_year_return,inception_date,aum,
    front_load,back_load,transaction_fee
    """

    REQUIRED_COLUMNS = ["ticker", "name", "fund_type"]

    OPTIONAL_COLUMNS = [
        "provider",
        "mer",
        "asset_class",
        "geographic_focus",
        "description",
        "ytd_return",
        "one_year_return",
        "three_year_return",
        "five_year_return",
        "ten_year_return",
        "inception_date",
        "aum",
        "minimum_investment",
        "front_load",
        "back_load",
        "transaction_fee",
        "data_source_url",
    ]

    def __init__(self, csv_path: Optional[str] = None, **kwargs):
        """
        Initialize CSV source.

        Args:
            csv_path: Path to CSV file (optional, can be set later)
        """
        super().__init__(**kwargs)
        self.csv_path = Path(csv_path) if csv_path else None
        self._cached_data = {}  # In-memory cache of CSV data

    def load_csv(self, csv_path: str) -> List[FundDataDTO]:
        """
        Load all funds from a CSV file.

        Args:
            csv_path: Path to CSV file

        Returns:
            List of FundDataDTO objects

        Raises:
            FileNotFoundError: If CSV file doesn't exist
            ValueError: If CSV format is invalid
        """
        csv_path = Path(csv_path)

        if not csv_path.exists():
            raise FileNotFoundError(f"CSV file not found: {csv_path}")

        logger.info(f"[CSV] Loading funds from {csv_path}")

        funds = []
        with open(csv_path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)

            # Validate headers
            self._validate_headers(reader.fieldnames)

            # Parse each row
            for row_num, row in enumerate(reader, start=2):  # Start at 2 (header is row 1)
                try:
                    fund_data = self._parse_row(row)
                    if fund_data:
                        funds.append(fund_data)
                        # Cache for later fetch_fund() calls
                        self._cached_data[fund_data.ticker] = fund_data
                except Exception as e:
                    logger.error(f"[CSV] Error parsing row {row_num}: {e}")
                    continue

        logger.info(f"[CSV] Loaded {len(funds)} funds from {csv_path}")
        self.csv_path = csv_path
        return funds

    def fetch_fund(self, ticker: str) -> Optional[FundDataDTO]:
        """
        Fetch a fund from the loaded CSV data.

        Args:
            ticker: Fund ticker

        Returns:
            FundDataDTO if found in CSV, None otherwise
        """
        # Check in-memory cache first
        if ticker in self._cached_data:
            return self._cached_data[ticker]

        # If CSV path is set, try to reload and search
        if self.csv_path:
            funds = self.load_csv(str(self.csv_path))
            for fund in funds:
                if fund.ticker == ticker:
                    return fund

        return None

    def _validate_headers(self, headers: List[str]):
        """Validate that CSV has required columns."""
        if not headers:
            raise ValueError("CSV file is empty or has no headers")

        missing = [col for col in self.REQUIRED_COLUMNS if col not in headers]
        if missing:
            raise ValueError(f"CSV missing required columns: {missing}")

    def _parse_row(self, row: dict) -> Optional[FundDataDTO]:
        """Parse a CSV row into FundDataDTO."""
        # Required fields
        ticker = row.get("ticker", "").strip()
        name = row.get("name", "").strip()
        fund_type = row.get("fund_type", "").strip().upper()

        if not all([ticker, name, fund_type]):
            logger.warning(f"[CSV] Skipping row with missing required fields: {row}")
            return None

        # Parse optional fields
        def get_decimal(field_name: str) -> Optional[Decimal]:
            """Safely parse decimal field."""
            value = row.get(field_name, "").strip()
            if not value or value.lower() in ["", "n/a", "na", "none", "-"]:
                return None
            try:
                return Decimal(value)
            except (InvalidOperation, ValueError):
                logger.warning(f"[CSV] Invalid decimal value for {field_name}: {value}")
                return None

        def get_date(field_name: str) -> Optional[date]:
            """Safely parse date field (YYYY-MM-DD format)."""
            value = row.get(field_name, "").strip()
            if not value or value.lower() in ["", "n/a", "na", "none", "-"]:
                return None
            try:
                return datetime.strptime(value, "%Y-%m-%d").date()
            except ValueError:
                logger.warning(f"[CSV] Invalid date format for {field_name}: {value} (expected YYYY-MM-DD)")
                return None

        # Build FundDataDTO
        return FundDataDTO(
            ticker=ticker,
            name=name,
            fund_type=fund_type,
            provider_name=row.get("provider", "").strip() or None,
            mer=get_decimal("mer"),
            front_load=get_decimal("front_load") or Decimal("0.00"),
            back_load=get_decimal("back_load") or Decimal("0.00"),
            transaction_fee=get_decimal("transaction_fee") or Decimal("0.00"),
            asset_class=row.get("asset_class", "").strip().upper() or None,
            geographic_focus=row.get("geographic_focus", "").strip().upper() or None,
            description=row.get("description", "").strip() or None,
            ytd_return=get_decimal("ytd_return"),
            one_year_return=get_decimal("one_year_return"),
            three_year_return=get_decimal("three_year_return"),
            five_year_return=get_decimal("five_year_return"),
            ten_year_return=get_decimal("ten_year_return"),
            inception_date=get_date("inception_date"),
            aum=get_decimal("aum"),
            minimum_investment=get_decimal("minimum_investment"),
            data_source_url=row.get("data_source_url", "").strip() or None,
            last_data_update=date.today(),
            source_name="CSV",
        )

    def supports_fund_type(self, fund_type: str) -> bool:
        """CSV supports both ETFs and mutual funds."""
        return fund_type in ["ETF", "MUTUAL_FUND"]

    def get_source_info(self) -> dict:
        """Get information about CSV source."""
        info = super().get_source_info()
        info.update(
            {
                "description": "CSV file import",
                "best_for": "Manual data entry, mutual funds",
                "requires_api_key": False,
                "csv_path": str(self.csv_path) if self.csv_path else None,
                "loaded_funds": len(self._cached_data),
            }
        )
        return info

    @staticmethod
    def generate_sample_csv(output_path: str):
        """
        Generate a sample CSV file with example funds.

        Args:
            output_path: Path where sample CSV should be created
        """
        sample_data = [
            {
                "ticker": "VFV.TO",
                "name": "Vanguard S&P 500 Index ETF",
                "provider": "Vanguard",
                "fund_type": "ETF",
                "mer": "0.08",
                "asset_class": "EQUITY",
                "geographic_focus": "US",
                "description": "Tracks the S&P 500 Index",
                "one_year_return": "15.2",
                "three_year_return": "12.5",
                "five_year_return": "13.8",
                "inception_date": "2012-11-02",
                "aum": "5000.00",
                "front_load": "0.00",
                "back_load": "0.00",
                "transaction_fee": "0.00",
            },
            {
                "ticker": "TDB902",
                "name": "TD U.S. Index Fund - e Series",
                "provider": "TD Asset Management",
                "fund_type": "MUTUAL_FUND",
                "mer": "0.35",
                "asset_class": "EQUITY",
                "geographic_focus": "US",
                "description": "Low-cost index mutual fund tracking U.S. equity market",
                "one_year_return": "14.8",
                "three_year_return": "12.0",
                "five_year_return": "13.5",
                "inception_date": "2000-01-01",
                "aum": "2500.00",
                "front_load": "0.00",
                "back_load": "0.00",
                "transaction_fee": "0.00",
            },
            {
                "ticker": "RBF556",
                "name": "RBC Select Balanced Portfolio",
                "provider": "RBC",
                "fund_type": "MUTUAL_FUND",
                "mer": "2.04",
                "asset_class": "BALANCED",
                "geographic_focus": "GLOBAL",
                "description": "Actively managed balanced fund with stocks and bonds",
                "one_year_return": "8.5",
                "three_year_return": "7.2",
                "five_year_return": "6.8",
                "inception_date": "1995-06-15",
                "aum": "1200.00",
                "front_load": "5.00",
                "back_load": "5.00",
                "transaction_fee": "0.00",
            },
        ]

        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        with open(output_path, "w", newline="", encoding="utf-8") as f:
            fieldnames = list(sample_data[0].keys())
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(sample_data)

        logger.info(f"[CSV] Generated sample CSV at {output_path}")
        return output_path
