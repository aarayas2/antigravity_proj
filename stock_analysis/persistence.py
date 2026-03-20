"""
Persistence layer for storing and retrieving statistics.
"""

import json
import os
import threading
from abc import ABC, abstractmethod
from typing import Dict, Any, List

class StatsStorageStrategy(ABC):
    """Abstract base class for storage strategies."""

    @abstractmethod
    def read(self) -> List[Dict[str, Any]]:
        """Reads data from the storage."""

    @abstractmethod
    def write(self, data: List[Dict[str, Any]]) -> None:
        """Writes data to the storage."""


class JsonStatsStorage(StatsStorageStrategy):
    """Storage strategy for JSON files."""
    def __init__(self, file_path: str):
        self.file_path = file_path
        # Ensure directory exists
        os.makedirs(os.path.dirname(self.file_path), exist_ok=True)
        if not os.path.exists(self.file_path):
            with open(self.file_path, 'w', encoding='utf-8') as f:
                json.dump([], f)

    def read(self) -> List[Dict[str, Any]]:
        if not os.path.exists(self.file_path):
            return []

        with open(self.file_path, 'r', encoding='utf-8') as f:
            try:
                data = json.load(f)
                if not isinstance(data, list):
                    data = []
            except json.JSONDecodeError:
                data = []
        return data

    def write(self, data: List[Dict[str, Any]]) -> None:
        # Write to a temp file first for atomic replacement (prevents corruption)
        temp_path = self.file_path + '.tmp'

        try:
            with open(temp_path, 'w', encoding='utf-8') as tf:
                json.dump(data, tf, indent=2)
            # Atomic replace works cross-platform
            os.replace(temp_path, self.file_path)
        except Exception as e:
            if os.path.exists(temp_path):
                os.remove(temp_path)
            raise e

class StatsManager:
    """Manages the saving and updating of statistics via a storage strategy."""
    _instance = None
    _lock = threading.Lock()
    _storage = None

    def __new__(cls, storage_strategy: StatsStorageStrategy = None):
        with cls._lock:
            if cls._instance is None:
                if storage_strategy is None:
                    raise ValueError(
                        "A storage strategy must be provided for the first initialization."
                    )
                cls._instance = super(StatsManager, cls).__new__(cls)
                cls._instance._storage = storage_strategy
            return cls._instance

    def __init__(self, storage_strategy: StatsStorageStrategy = None):
        # Prevent re-initialization if already instantiated
        pass

    def save_stats(
        self, ticker: str, date_begin: str, date_end: str,
        strategies_metrics: Dict[str, Dict[str, Any]]
    ):
        """
        Saves or updates the statistics for a ticker.
        """
        self.save_stats_batch([{
            "ticker": ticker,
            "date_begin": date_begin,
            "date_end": date_end,
            "strategies_metrics": strategies_metrics
        }])

    def read_all_stats(self) -> List[Dict[str, Any]]:
        """
        Reads and returns all currently stored statistics.
        """
        with self._lock:
            return self._storage.read()

    def save_stats_batch(self, batch_data: List[Dict[str, Any]]):
        """
        Saves or updates statistics for a batch of tickers to avoid repeated I/O operations.
        Each item must contain 'ticker', 'date_begin', 'date_end', and 'strategies_metrics'.
        """
        if not batch_data:
            return

        with self._lock: # Thread-safety at the application level
            data = self._storage.read()

            # Create a mapping for O(1) lookups and updates
            # Using the first key as the ticker identifier
            data_dict = {
                k: (i, e[k])
                for i, e in enumerate(data)
                for k in [next(iter(e))]
            }

            modified = False
            for item in batch_data:
                ticker = item['ticker'].upper()
                date_begin = item['date_begin']
                date_end = item['date_end']
                strategies_metrics = item['strategies_metrics']

                new_entry_data = {
                    "date-begin": date_begin,
                    "date-end": date_end,
                }
                new_entry_data.update(strategies_metrics)

                if ticker in data_dict:
                    idx, existing_entry = data_dict[ticker]
                    if (existing_entry.get("date-begin") == date_begin and
                            existing_entry.get("date-end") == date_end):
                        pass # No operation needed
                    else:
                        data[idx][ticker] = new_entry_data
                        modified = True
                else:
                    data.append({ticker: new_entry_data})
                    data_dict[ticker] = (len(data) - 1, new_entry_data)
                    modified = True

            if modified:
                self._storage.write(data)
