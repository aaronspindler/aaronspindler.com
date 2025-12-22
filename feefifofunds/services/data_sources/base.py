import time
from abc import ABC, abstractmethod
from datetime import date
from typing import List

import requests


class DataSourceError(Exception):
    pass


class RateLimitError(DataSourceError):
    pass


class DataNotFoundError(DataSourceError):
    pass


class BaseDataSource(ABC):
    name: str
    display_name: str
    base_url: str
    requires_api_key: bool = True

    def __init__(self, api_key: str = None):
        self.api_key = api_key
        self.session = requests.Session()
        if api_key:
            self.session.headers.update({"Authorization": f"Bearer {api_key}"})

    @abstractmethod
    def fetch_historical_prices(self, ticker: str, start_date: date, end_date: date) -> List[dict]:
        pass

    def _make_request(self, url: str, params: dict = None, max_retries: int = 3) -> dict:
        for attempt in range(max_retries):
            try:
                response = self.session.get(url, params=params, timeout=30)

                if response.status_code == 429:
                    raise RateLimitError(f"Rate limit exceeded for {self.name}")

                if response.status_code == 404:
                    raise DataNotFoundError(f"Data not found: {url}")

                response.raise_for_status()
                return response.json()

            except requests.exceptions.Timeout as e:
                if attempt == max_retries - 1:
                    raise DataSourceError(f"Request timeout after {max_retries} attempts") from e
                time.sleep(2**attempt)

            except requests.exceptions.RequestException as e:
                if attempt == max_retries - 1:
                    raise DataSourceError(f"Request failed: {str(e)}") from e
                time.sleep(2**attempt)

        raise DataSourceError("Max retries exceeded")
