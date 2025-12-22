import logging
from datetime import datetime
from typing import Any, List

from django.db import connections

from feefifofunds.config.database_pool import ConnectionPoolManager

logger = logging.getLogger(__name__)


class QuestDBClient:
    def __init__(self, database: str = "questdb"):
        self.database = database

    def execute_query(self, query: str, params: List[Any] | None = None) -> List[tuple]:
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
        try:
            return int(value)
        except (TypeError, ValueError) as e:
            raise ValueError(f"Invalid {param_name}: expected integer, got {type(value).__name__}") from e

    def _validate_datetime(self, value: Any, param_name: str) -> datetime:
        if not isinstance(value, datetime):
            raise ValueError(f"Invalid {param_name}: expected datetime, got {type(value).__name__}")
        return value

    def check_pool_health(self) -> bool:
        return ConnectionPoolManager.monitor_pool_health(self.database)

    def get_pool_stats(self) -> dict:
        return ConnectionPoolManager.get_pool_stats(self.database)

    def warm_pool(self, num_connections: int = 5):
        ConnectionPoolManager.warm_connection_pool(self.database, num_connections)
