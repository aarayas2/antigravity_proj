import json
import os
import threading
from abc import ABC, abstractmethod
from typing import Dict, Any, List

class StatsStorageStrategy(ABC):
    @abstractmethod
    def read(self) -> List[Dict[str, Any]]:
        pass

    @abstractmethod
    def write(self, data: List[Dict[str, Any]]) -> None:
        pass


class JsonStatsStorage(StatsStorageStrategy):
    def __init__(self, file_path: str):
        self.file_path = file_path
        # Ensure directory exists
        os.makedirs(os.path.dirname(self.file_path), exist_ok=True)
        if not os.path.exists(self.file_path):
            with open(self.file_path, 'w') as f:
                json.dump([], f)

    def read(self) -> List[Dict[str, Any]]:
        if not os.path.exists(self.file_path):
            return []
            
        with open(self.file_path, 'r') as f:
            try:
                data = json.load(f)
                if not isinstance(data, list):
                    data = []
            except json.JSONDecodeError:
                data = []
        return data

    def write(self, data: List[Dict[str, Any]]) -> None:
        # Write to a temporary file first for atomic replacement (error handling/corruption prevention)
        temp_path = self.file_path + '.tmp'
        
        try:
            with open(temp_path, 'w') as tf:
                json.dump(data, tf, indent=2)
            # Atomic replace works cross-platform
            os.replace(temp_path, self.file_path)
        except Exception as e:
            if os.path.exists(temp_path):
                os.remove(temp_path)
            raise e

class StatsManager:
    _instance = None
    _lock = threading.Lock()

    def __new__(cls, storage_strategy: StatsStorageStrategy = None):
        with cls._lock:
            if cls._instance is None:
                if storage_strategy is None:
                    raise ValueError("A storage strategy must be provided for the first initialization.")
                cls._instance = super(StatsManager, cls).__new__(cls)
                cls._instance._storage = storage_strategy
            return cls._instance

    def __init__(self, storage_strategy: StatsStorageStrategy = None):
        # Prevent re-initialization if already instantiated
        pass

    def save_stats(self, ticker: str, date_begin: str, date_end: str, strategies_metrics: Dict[str, Dict[str, Any]]):
        """
        Saves or updates the statistics for a ticker.
        """
        with self._lock: # Thread-safety at the application level
            data = self._storage.read()
            
            ticker = ticker.upper()
            
            # Find if ticker exists
            existing_idx = None
            for idx, entry in enumerate(data):
                if ticker in entry:
                    existing_idx = idx
                    break
            
            new_entry_data = {
                "date-begin": date_begin,
                "date-end": date_end,
            }
            new_entry_data.update(strategies_metrics)
            
            if existing_idx is not None:
                existing_entry = data[existing_idx][ticker]
                # If ticker exists with same date range, do nothing
                if existing_entry.get("date-begin") == date_begin and existing_entry.get("date-end") == date_end:
                    return # No operation needed
                else:
                    # If date range differs, overwrite
                    data[existing_idx][ticker] = new_entry_data
            else:
                # If ticker does not exist, append it
                data.append({ticker: new_entry_data})
                
            self._storage.write(data)

