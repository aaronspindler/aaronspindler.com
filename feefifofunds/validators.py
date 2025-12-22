from datetime import datetime
from typing import List, Literal

from pydantic import BaseModel, Field, field_validator


class IngestionConfig(BaseModel):
    tier: Literal["TIER1", "TIER2", "TIER3", "TIER4", "ALL"]
    intervals: List[int] = Field(min_length=1)
    start_date: datetime | None = None
    end_date: datetime | None = None
    lookback_days: int = Field(default=7, gt=0, le=365)
    max_gaps_per_asset: int = Field(default=10, gt=0, le=100)
    api_backfill_enabled: bool = True
    auto_gap_fill: bool = True

    @field_validator("intervals")
    @classmethod
    def validate_intervals(cls, v: List[int]) -> List[int]:
        valid_intervals = {1, 5, 15, 30, 60, 240, 1440, 10080, 21600}
        for interval in v:
            if interval not in valid_intervals:
                raise ValueError(f"Invalid interval: {interval}. Must be one of {valid_intervals}")
        return v

    @field_validator("end_date")
    @classmethod
    def validate_end_date(cls, v: datetime | None, info) -> datetime | None:
        if v is not None and info.data.get("start_date") is not None:
            if v <= info.data["start_date"]:
                raise ValueError("end_date must be after start_date")
        return v

    class Config:
        json_schema_extra = {
            "example": {
                "tier": "TIER1",
                "intervals": [60, 1440],
                "start_date": "2020-01-01T00:00:00",
                "end_date": "2024-12-31T23:59:59",
                "lookback_days": 7,
                "max_gaps_per_asset": 10,
            }
        }


class GapBackfillConfig(BaseModel):
    asset_id: int = Field(gt=0)
    interval_minutes: int
    gap_start: datetime
    gap_end: datetime
    max_retries: int = Field(default=3, ge=0, le=10)
    retry_delay: float = Field(default=1.0, gt=0, le=60)

    @field_validator("interval_minutes")
    @classmethod
    def validate_interval(cls, v: int) -> int:
        valid_intervals = {1, 5, 15, 30, 60, 240, 1440, 10080, 21600}
        if v not in valid_intervals:
            raise ValueError(f"Invalid interval: {v}")
        return v

    @field_validator("gap_end")
    @classmethod
    def validate_gap_end(cls, v: datetime, info) -> datetime:
        if "gap_start" in info.data and v <= info.data["gap_start"]:
            raise ValueError("gap_end must be after gap_start")
        return v


class AssetQueryParams(BaseModel):
    asset_id: int = Field(gt=0)
    ticker: str | None = Field(default=None, pattern="^[A-Z]{2,10}(USD)?$")
    tier: Literal["TIER1", "TIER2", "TIER3", "TIER4", "ALL"] | None = None
    active_only: bool = True

    @field_validator("ticker")
    @classmethod
    def validate_ticker(cls, v: str | None) -> str | None:
        if v:
            return v.upper().replace("-", "")
        return v


class DateRangeParams(BaseModel):
    start_date: datetime
    end_date: datetime
    max_days: int = Field(default=3650, gt=0)  # Max 10 years

    @field_validator("end_date")
    @classmethod
    def validate_date_range(cls, v: datetime, info) -> datetime:
        if "start_date" not in info.data:
            return v

        start_date = info.data["start_date"]
        if v <= start_date:
            raise ValueError("end_date must be after start_date")

        days_diff = (v - start_date).days
        max_days = info.data.get("max_days", 3650)
        if days_diff > max_days:
            raise ValueError(f"Date range cannot exceed {max_days} days")

        if v > datetime.now():
            raise ValueError("end_date cannot be in the future")

        return v


class DatabaseQueryParams(BaseModel):
    table_name: Literal["assetprice", "asset", "ingestion_job", "gap_record"]
    asset_id: int | None = Field(default=None, gt=0)
    interval_minutes: int | None = None
    limit: int = Field(default=1000, gt=0, le=10000)
    offset: int = Field(default=0, ge=0)
    order_by: Literal["time", "asset_id", "interval_minutes", "-time", "-asset_id"] = "time"

    @field_validator("interval_minutes")
    @classmethod
    def validate_interval(cls, v: int | None) -> int | None:
        if v is not None:
            valid_intervals = {1, 5, 15, 30, 60, 240, 1440, 10080, 21600}
            if v not in valid_intervals:
                raise ValueError(f"Invalid interval: {v}")
        return v

    def to_safe_params(self) -> dict:
        params = {}
        if self.asset_id is not None:
            params["asset_id"] = int(self.asset_id)
        if self.interval_minutes is not None:
            params["interval_minutes"] = int(self.interval_minutes)
        params["limit"] = int(self.limit)
        params["offset"] = int(self.offset)
        return params


class CeleryTaskConfig(BaseModel):
    task_name: str = Field(pattern="^[a-z_]+\\.[a-z_]+$")
    tier: Literal["TIER1", "TIER2", "TIER3", "TIER4", "ALL"]
    intervals: List[int] = Field(min_length=1)
    schedule: str = Field(pattern="^(\\*/)?[0-9]+(,[0-9]+)*\\s+.*$")  # Cron pattern
    enabled: bool = True
    max_retries: int = Field(default=3, ge=0, le=10)
    retry_delay: int = Field(default=60, gt=0, le=3600)

    @field_validator("intervals")
    @classmethod
    def validate_intervals(cls, v: List[int]) -> List[int]:
        valid_intervals = {1, 5, 15, 30, 60, 240, 1440, 10080, 21600}
        for interval in v:
            if interval not in valid_intervals:
                raise ValueError(f"Invalid interval: {interval}")
        return v


# Validation helper functions


def validate_asset_ticker(ticker: str) -> str:
    if not ticker:
        raise ValueError("Ticker cannot be empty")

    ticker = ticker.upper().strip()

    # Check format (2-10 uppercase letters, optionally followed by USD)
    import re

    if not re.match(r"^[A-Z]{2,10}(USD)?$", ticker):
        raise ValueError(f"Invalid ticker format: {ticker}")

    return ticker


def validate_tier(tier: str) -> str:
    valid_tiers = {"TIER1", "TIER2", "TIER3", "TIER4", "ALL"}
    tier = tier.upper()

    if tier not in valid_tiers:
        raise ValueError(f"Invalid tier: {tier}. Must be one of {valid_tiers}")

    return tier


def validate_interval_minutes(interval: int) -> int:
    valid_intervals = {1, 5, 15, 30, 60, 240, 1440, 10080, 21600}

    if interval not in valid_intervals:
        raise ValueError(f"Invalid interval: {interval}. Must be one of {valid_intervals}")

    return interval


def sanitize_sql_identifier(identifier: str) -> str:
    import re

    if not re.match(r"^[a-zA-Z_][a-zA-Z0-9_]*$", identifier):
        raise ValueError(f"Invalid SQL identifier: {identifier}")

    return identifier
