from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Optional


@dataclass
class PriceDataDTO:
    ticker: str
    timestamp: datetime
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    volume: Optional[Decimal] = None
    source: str = "unknown"

    def __post_init__(self):
        if not self.ticker:
            raise ValueError("Ticker is required")
        if not self.timestamp:
            raise ValueError("Timestamp is required")
        if self.close is None:
            raise ValueError("Close price is required")

        def _to_decimal(value, max_places=8):
            if value is None:
                return None
            if isinstance(value, (int, float)):
                value = Decimal(str(value))
            if value.as_tuple().exponent < -max_places:
                value = round(value, max_places)
            return value

        self.open = _to_decimal(self.open)
        self.high = _to_decimal(self.high)
        self.low = _to_decimal(self.low)
        self.close = _to_decimal(self.close)
        self.volume = _to_decimal(self.volume, max_places=2) if self.volume else None
