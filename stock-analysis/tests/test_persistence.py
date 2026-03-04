import json
import pytest
import sys
import os

# Add the parent directory of stock-analysis to sys.path so we can import it
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from persistence import JsonStatsStorage

def test_read_file_not_exists(tmp_path):
    file_path = tmp_path / "non_existent.json"
    # JsonStatsStorage.__init__ creates the file with [] if it doesn't exist.
    storage = JsonStatsStorage(str(file_path))

    # To test the read logic where the file really doesn't exist, we must delete it after init.
    if os.path.exists(str(file_path)):
        os.remove(str(file_path))

    assert storage.read() == []

def test_read_valid_list(tmp_path):
    file_path = tmp_path / "valid_list.json"
    data = [{"TICKER": {"date-begin": "2023-01-01", "date-end": "2023-12-31"}}]
    with open(file_path, 'w') as f:
        json.dump(data, f)

    storage = JsonStatsStorage(str(file_path))
    assert storage.read() == data

def test_read_non_list_json(tmp_path):
    file_path = tmp_path / "non_list.json"
    data = {"key": "value"}
    with open(file_path, 'w') as f:
        json.dump(data, f)

    storage = JsonStatsStorage(str(file_path))
    assert storage.read() == []

def test_read_malformed_json(tmp_path):
    file_path = tmp_path / "malformed.json"
    with open(file_path, 'w') as f:
        f.write("{ invalid json")

    storage = JsonStatsStorage(str(file_path))
    assert storage.read() == []
