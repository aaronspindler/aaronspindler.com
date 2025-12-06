"""
QuestDB Query Client for safe database queries.

This module provides a safe interface for querying QuestDB with proper
parameter validation and SQL injection prevention.
"""

import logging
from datetime import datetime
from typing import Any, List

from django.db import connections

from feefifofunds.config.database_pool import ConnectionPoolManager

logger = logging.getLogger(__name__)


class QuestDBClient:
    """
    Safe client for querying QuestDB with parameter validation.

    Uses Django's database connection with proper parameter escaping
    to prevent SQL injection vulnerabilities.
    """

    def __init__(self, database: str = "questdb"):
        """
        Initialize QuestDB client.

        Args:
            database: Database alias from Django settings (default: questdb)
        """
        self.database = database

    def execute_query(self, query: str, params: List[Any] | None = None) -> List[tuple]:
        """
        Execute a parameterized query against QuestDB.

        Args:
            query: SQL query with %s placeholders for parameters
            params: List of parameters to safely substitute

        Returns:
            List of result tuples

        Example:
            query = "SELECT * FROM table WHERE id = %s AND value > %s"
            results = client.execute_query(query, [123, 50.0])
        """
        try:
            with connections[self.database].cursor() as cursor:
                if params:
                    cursor.execute(query, params)
                else:
                    cursor.execute(query)

                results = cursor.fetchall()
                return results

        except Exception as e:
            logger.error(f"QuestDB query error: {e}", exc_info=True)
            logger.error(f"Query: {query}")
            logger.error(f"Params: {params}")
            raise

    def get_date_range_for_asset(self, asset_id: int, interval_minutes: int) -> tuple[datetime, datetime, int] | None:
        """
        Get date range and record count for an asset/interval.

        Args:
            asset_id: Asset ID (validated as integer)
            interval_minutes: Interval in minutes (validated as integer)

        Returns:
            Tuple of (start_date, end_date, record_count) or None if no data

        Raises:
            ValueError: If parameters are not valid integers
        """
        # Validate parameters to prevent SQL injection
        asset_id = self._validate_int(asset_id, "asset_id")
        interval_minutes = self._validate_int(interval_minutes, "interval_minutes")

        query = """
            SELECT
                MIN(time) as start_date,
                MAX(time) as end_date,
                COUNT(*) as record_count
            FROM assetprice
            WHERE asset_id = %s
              AND interval_minutes = %s
        """

        results = self.execute_query(query, [asset_id, interval_minutes])

        if not results or len(results) == 0:
            return None

        row = results[0]

        # Check if any data exists
        if row[0] is None or row[1] is None:
            return None

        return row[0], row[1], row[2]

    def count_candles(
        self,
        asset_id: int,
        interval_minutes: int,
        start_date: datetime,
        end_date: datetime,
    ) -> int:
        """
        Count candles for an asset/interval in a date range.

        Args:
            asset_id: Asset ID (validated as integer)
            interval_minutes: Interval in minutes (validated as integer)
            start_date: Range start
            end_date: Range end

        Returns:
            Candle count

        Raises:
            ValueError: If parameters are not valid
        """
        # Validate parameters
        asset_id = self._validate_int(asset_id, "asset_id")
        interval_minutes = self._validate_int(interval_minutes, "interval_minutes")
        self._validate_datetime(start_date, "start_date")
        self._validate_datetime(end_date, "end_date")

        query = """
            SELECT COUNT(*) as count
            FROM assetprice
            WHERE asset_id = %s
              AND interval_minutes = %s
              AND time >= %s
              AND time <= %s
        """

        results = self.execute_query(query, [asset_id, interval_minutes, start_date, end_date])

        if results and len(results) > 0:
            return results[0][0]
        return 0

    def get_last_timestamp(self, asset_id: int, interval_minutes: int) -> datetime | None:
        """
        Get the most recent timestamp for an asset/interval.

        Args:
            asset_id: Asset ID (validated as integer)
            interval_minutes: Interval in minutes (validated as integer)

        Returns:
            Most recent timestamp or None if no data

        Raises:
            ValueError: If parameters are not valid integers
        """
        # Validate parameters
        asset_id = self._validate_int(asset_id, "asset_id")
        interval_minutes = self._validate_int(interval_minutes, "interval_minutes")

        query = """
            SELECT MAX(time) as last_timestamp
            FROM assetprice
            WHERE asset_id = %s
              AND interval_minutes = %s
        """

        results = self.execute_query(query, [asset_id, interval_minutes])

        if results and len(results) > 0 and results[0][0] is not None:
            return results[0][0]
        return None

    def _validate_int(self, value: Any, param_name: str) -> int:
        """
        Validate that a value is an integer.

        Args:
            value: Value to validate
            param_name: Parameter name for error message

        Returns:
            Validated integer value

        Raises:
            ValueError: If value is not a valid integer
        """
        try:
            return int(value)
        except (TypeError, ValueError) as e:
            raise ValueError(f"Invalid {param_name}: expected integer, got {type(value).__name__}") from e

    def _validate_datetime(self, value: Any, param_name: str) -> datetime:
        """
        Validate that a value is a datetime.

        Args:
            value: Value to validate
            param_name: Parameter name for error message

        Returns:
            Validated datetime value

        Raises:
            ValueError: If value is not a valid datetime
        """
        if not isinstance(value, datetime):
            raise ValueError(f"Invalid {param_name}: expected datetime, got {type(value).__name__}")
        return value

    def check_pool_health(self) -> bool:
        """
        Check if the connection pool is healthy.

        Returns:
            True if pool is healthy, False otherwise
        """
        return ConnectionPoolManager.monitor_pool_health(self.database)

    def get_pool_stats(self) -> dict:
        """
        Get current connection pool statistics.

        Returns:
            Dictionary with pool statistics
        """
        return ConnectionPoolManager.get_pool_stats(self.database)

    def warm_pool(self, num_connections: int = 5):
        """
        Pre-warm the connection pool.

        Args:
            num_connections: Number of connections to pre-establish
        """
        ConnectionPoolManager.warm_connection_pool(self.database, num_connections)
