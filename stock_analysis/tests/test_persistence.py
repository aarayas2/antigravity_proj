"""
Unit tests for persistence.py.
"""
# pylint: disable=too-few-public-methods,line-too-long,import-error,useless-parent-delegation,protected-access,unused-variable,unnecessary-pass,too-many-lines
import json
import os
import sys
from unittest.mock import patch, mock_open

import pytest

# Add the parent directory of stock_analysis to sys.path so we can import it
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from persistence import JsonStatsStorage, StatsManager, StatsStorageStrategy  # pylint: disable=import-error, wrong-import-position

def test_read_file_not_exists(tmp_path):
    """Test read file not exists."""
    file_path = tmp_path / "non_existent.json"
    # JsonStatsStorage.__init__ creates the file with [] if it doesn't exist.
    storage = JsonStatsStorage(str(file_path))

    # To test the read logic where the file really doesn't exist, we must delete it after init.
    if os.path.exists(str(file_path)):
        os.remove(str(file_path))

    assert not storage.read()

def test_read_valid_list(tmp_path):
    """Test read valid list."""
    file_path = tmp_path / "valid_list.json"
    data = [{"TICKER": {"date-begin": "2023-01-01", "date-end": "2023-12-31"}}]
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(data, f)

    storage = JsonStatsStorage(str(file_path))
    assert storage.read() == data

def test_read_non_list_json(tmp_path):
    """Test read non list json."""
    file_path = tmp_path / "non_list.json"
    data = {"key": "value"}
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(data, f)

    storage = JsonStatsStorage(str(file_path))
    assert not storage.read()

def test_read_malformed_json(tmp_path):
    """Test read malformed json."""
    file_path = tmp_path / "malformed.json"
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write("{ invalid json")

    storage = JsonStatsStorage(str(file_path))
    assert not storage.read()

def test_write_success(tmp_path):
    """Test write success."""
    file_path = tmp_path / "write.json"
    storage = JsonStatsStorage(str(file_path))
    data = [{"TICKER": {"date-begin": "2023-01-01", "date-end": "2023-12-31"}}]

    storage.write(data)

    # Verify file was written correctly
    assert os.path.exists(str(file_path))
    with open(file_path, 'r', encoding='utf-8') as f:
        written_data = json.load(f)
    assert written_data == data

def test_write_exception_removes_temp_file(tmp_path):
    """Test exception removes temp file."""
    file_path = tmp_path / "write_fail.json"
    storage = JsonStatsStorage(str(file_path))
    data = [{"TICKER": {"date-begin": "2023-01-01", "date-end": "2023-12-31"}}]

    # Mock os.replace to raise an exception, simulating a failure during the atomic replace
    with patch("os.replace", side_effect=OSError("Mocked error")):
        with pytest.raises(OSError):
            storage.write(data)

    # temp file should have been cleaned up
    temp_path = str(file_path) + '.tmp'
    assert not os.path.exists(temp_path)

def test_write_exception_when_temp_file_doesnt_exist_anymore(tmp_path):
    """Test exception when temp file doesnt exist."""
    file_path = tmp_path / "write_fail_no_temp.json"
    storage = JsonStatsStorage(str(file_path))
    data = [{"TICKER": {"date-begin": "2023-01-01", "date-end": "2023-12-31"}}]

    # Mock os.replace to raise an exception, and mock os.path.exists to return False for the temp file
    # This hits the 'if os.path.exists(temp_path):' branch evaluating to False inside the except block
    with patch("os.replace", side_effect=OSError("Mocked error")), \
         patch("os.path.exists", side_effect=lambda p: not p.endswith('.tmp')):
        with pytest.raises(OSError):
            storage.write(data)

def test_stats_manager_init_without_strategy_raises_error():
    """Test StatsManager init without strategy raises error."""
    # Reset singleton instance to test first initialization
    StatsManager._instance = None  # pylint: disable=protected-access

    with pytest.raises(ValueError, match="A storage strategy must be provided for the first initialization."):
        StatsManager()


def test_stats_manager_singleton():
    """Test stats manager singleton."""
    # Reset singleton instance for testing
    StatsManager._instance = None  # pylint: disable=protected-access

    # Needs a strategy for first init
    with pytest.raises(ValueError, match="A storage strategy must be provided for the first initialization."):
        StatsManager()

    class MockStorage(StatsStorageStrategy):
        """Mock storage."""
        def read(self):
            """Read method mock."""
            return []

        def write(self, data):
            """Write method mock."""
            pass


    storage1 = MockStorage()
    manager1 = StatsManager(storage1)

    # Second init ignores the passed strategy and returns the same instance
    storage2 = MockStorage()
    manager2 = StatsManager(storage2)

    assert manager1 is manager2
    assert manager1._storage is storage1

def test_stats_manager_save_stats_new_ticker(tmp_path):
    """Test save stats new ticker."""
    StatsManager._instance = None  # pylint: disable=protected-access
    file_path = tmp_path / "stats.json"
    storage = JsonStatsStorage(str(file_path))
    manager = StatsManager(storage)

    manager.save_stats(
        ticker="AAPL",
        date_begin="2023-01-01",
        date_end="2023-12-31",
        strategies_metrics={"SMA": {"profit": 100}}
    )

    data = storage.read()
    assert len(data) == 1
    assert "AAPL" in data[0]
    assert data[0]["AAPL"]["date-begin"] == "2023-01-01"
    assert data[0]["AAPL"]["date-end"] == "2023-12-31"
    assert data[0]["AAPL"]["SMA"]["profit"] == 100

def test_stats_manager_save_stats_existing_ticker_same_dates(tmp_path):
    """Test save stats existing ticker same dates."""
    StatsManager._instance = None  # pylint: disable=protected-access
    file_path = tmp_path / "stats.json"
    storage = JsonStatsStorage(str(file_path))
    manager = StatsManager(storage)

    # Initial save
    manager.save_stats("AAPL", "2023-01-01", "2023-12-31", {"SMA": {"profit": 100}})

    # Save again with same dates but different metrics
    # It should early-return and do nothing
    manager.save_stats("AAPL", "2023-01-01", "2023-12-31", {"SMA": {"profit": 999}})

    data = storage.read()
    assert len(data) == 1
    assert data[0]["AAPL"]["SMA"]["profit"] == 100

def test_stats_manager_save_stats_existing_ticker_diff_dates(tmp_path):
    """Test save stats existing ticker diff dates."""
    StatsManager._instance = None  # pylint: disable=protected-access
    file_path = tmp_path / "stats.json"
    storage = JsonStatsStorage(str(file_path))
    manager = StatsManager(storage)

    # Initial save
    manager.save_stats("AAPL", "2023-01-01", "2023-12-31", {"SMA": {"profit": 100}})

    # Save again with different dates
    manager.save_stats("AAPL", "2023-01-01", "2024-01-01", {"SMA": {"profit": 200}})

    data = storage.read()
    assert len(data) == 1
    assert data[0]["AAPL"]["date-end"] == "2024-01-01"
    assert data[0]["AAPL"]["SMA"]["profit"] == 200

def test_stats_storage_strategy_abstract_methods():
    """Test abstract methods."""
    # Calling the abstract methods should do nothing/pass
    class ConcreteStrategy(StatsStorageStrategy):
        """Concrete Strategy."""
        def read(self):
            """Read method mock."""
            super().read()
            return []
        def write(self, data):
            """Write method mock."""
            super().write(data)

    strategy = ConcreteStrategy()
    assert not strategy.read()
    strategy.write([]) # Should not raise

def test_read_json_decode_error_mocked(tmp_path):
    """Test read json decode error mocked."""
    # Mocking open to read valid looking but invalid JSON to trigger JSONDecodeError explicitly
    file_path = tmp_path / "mocked_json.json"
    storage = JsonStatsStorage(str(file_path))

    # Ensure os.path.exists returns true so read doesn't early return
    file_path.touch()

    with patch("builtins.open", mock_open(read_data="{ invalid json")):
        assert not storage.read()

def test_read_valid_data_mocked(tmp_path):
    """Test read valid data mocked."""
    # Mocking open to read valid JSON
    file_path = tmp_path / "mocked_valid_json.json"
    storage = JsonStatsStorage(str(file_path))

    # Ensure os.path.exists returns true so read doesn't early return
    file_path.touch()

    valid_data = '[{"TICKER": {"date-begin": "2023-01-01"}}]'
    with patch("builtins.open", mock_open(read_data=valid_data)):
        assert storage.read() == [{"TICKER": {"date-begin": "2023-01-01"}}]

def test_write_error_path(tmp_path):
    """Test write error path."""
    file_path = tmp_path / "test_write.json"
    storage = JsonStatsStorage(str(file_path))
    data = [{"TICKER": {"date-begin": "2023-01-01", "date-end": "2023-12-31"}}]

    with patch('os.replace') as mock_replace:
        mock_replace.side_effect = Exception("Mocked exception")

        with pytest.raises(Exception, match="Mocked exception"):
            storage.write(data)

        # Verify that temp file was removed
        temp_path = str(file_path) + '.tmp'
        assert not os.path.exists(temp_path)

def test_stats_manager_save_stats_existing_ticker_different_entry_idx(tmp_path):
    """Test save stats existing ticker diff entry idx."""
    # Test branch where ticker is NOT in the first entry, covering 82->81
    StatsManager._instance = None  # pylint: disable=protected-access
    file_path = tmp_path / "stats.json"
    storage = JsonStatsStorage(str(file_path))
    manager = StatsManager(storage)

    # Initial save for MSFT
    manager.save_stats("MSFT", "2023-01-01", "2023-12-31", {"SMA": {"profit": 50}})
    # Save for AAPL (second entry)
    manager.save_stats("AAPL", "2023-01-01", "2023-12-31", {"SMA": {"profit": 100}})

    # Update AAPL (which is the second entry in data, so idx=0 loop will have AAPL in entry == False)
    manager.save_stats("AAPL", "2023-01-01", "2024-01-01", {"SMA": {"profit": 200}})

    data = storage.read()
    assert len(data) == 2
    assert "MSFT" in data[0]
    assert "AAPL" in data[1]
    assert data[1]["AAPL"]["SMA"]["profit"] == 200

def test_json_stats_storage_write_exception_path(tmp_path):
    """
    Missing error path test for JsonStatsStorage write method
    Testing the exception block requires mocking os.replace to raise an error
    and verifying the temp file cleanup, taking under 20 lines of code.
    """
    file_path = tmp_path / "test_write_err.json"
    storage = JsonStatsStorage(str(file_path))
    data = [{"TICKER": {"date-begin": "2023-01-01"}}]

    with patch('os.replace', side_effect=OSError("Mocked error during replace")):
        with pytest.raises(OSError, match="Mocked error during replace"):
            storage.write(data)

    # Verify the temporary file cleanup occurred in the exception block
    temp_path = str(file_path) + '.tmp'
    assert not os.path.exists(temp_path)

class TestJsonStatsStorageRead:
    """
    Explicit test class to comprehensively test the JsonStatsStorage.read method
    as requested: asserting empty lists are returned on failure and valid data
    is returned on success, using mocked open() or temporary directories.
    """

    def test_read_success_valid_data(self, tmp_path):
        """Test method."""
        file_path = tmp_path / "valid.json"
        storage = JsonStatsStorage(str(file_path))
        valid_data = [{"AAPL": {"date-begin": "2023-01-01"}}]

        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(valid_data, f)

        assert storage.read() == valid_data

    def test_read_failure_file_not_exists(self, tmp_path):
        """Test method."""
        file_path = tmp_path / "not_exists.json"
        storage = JsonStatsStorage(str(file_path))
        # Ensure it's deleted after init
        if os.path.exists(str(file_path)):
            os.remove(str(file_path))

        assert not storage.read()

    def test_read_failure_malformed_json(self, tmp_path):
        """Test method."""
        file_path = tmp_path / "malformed.json"
        storage = JsonStatsStorage(str(file_path))

        with open(file_path, 'w', encoding='utf-8') as f:
            f.write("{ invalid_json }")

        assert not storage.read()

    def test_read_failure_not_a_list(self, tmp_path):
        """Test method."""
        file_path = tmp_path / "not_list.json"
        storage = JsonStatsStorage(str(file_path))

        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump({"not": "a list"}, f)

        assert not storage.read()

    @patch("builtins.open", new_callable=mock_open, read_data="[{\"AAPL\": {}}]")
    def test_read_success_mocked(self, _mock_file, tmp_path):
        """Test method."""
        file_path = tmp_path / "mocked_success.json"
        storage = JsonStatsStorage(str(file_path))

        # Touch the file so os.path.exists passes in read()
        file_path.touch()

        assert storage.read() == [{"AAPL": {}}]

    @patch("builtins.open", new_callable=mock_open, read_data="{ bad json")
    def test_read_failure_mocked_decode_error(self, _mock_file, tmp_path):
        """Test method."""
        file_path = tmp_path / "mocked_fail.json"
        storage = JsonStatsStorage(str(file_path))
        file_path.touch()

        assert not storage.read()

class TestJsonStatsStorageReadComprehensive:
    """
    Explicit test class to comprehensively test the JsonStatsStorage.read method
    as requested: asserting empty lists are returned on failure and valid data
    is returned on success, using mocked open() or temporary directories.
    """

    def test_read_success_valid_data(self, tmp_path):
        """Test method."""
        file_path = tmp_path / "valid.json"
        storage = JsonStatsStorage(str(file_path))
        valid_data = [{"AAPL": {"date-begin": "2023-01-01"}}]

        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(valid_data, f)

        assert storage.read() == valid_data

    def test_read_failure_file_not_exists(self, tmp_path):
        """Test method."""
        file_path = tmp_path / "not_exists.json"
        storage = JsonStatsStorage(str(file_path))
        # Ensure it's deleted after init
        if os.path.exists(str(file_path)):
            os.remove(str(file_path))

        assert not storage.read()

    def test_read_failure_malformed_json(self, tmp_path):
        """Test method."""
        file_path = tmp_path / "malformed.json"
        storage = JsonStatsStorage(str(file_path))

        with open(file_path, 'w', encoding='utf-8') as f:
            f.write("{ invalid_json }")

        assert not storage.read()

    def test_read_failure_not_a_list(self, tmp_path):
        """Test method."""
        file_path = tmp_path / "not_list.json"
        storage = JsonStatsStorage(str(file_path))

        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump({"not": "a list"}, f)

        assert not storage.read()

    @patch("builtins.open", new_callable=mock_open, read_data="[{\"AAPL\": {}}]")
    def test_read_success_mocked(self, _mock_file, tmp_path):
        """Test method."""
        file_path = tmp_path / "mocked_success.json"
        storage = JsonStatsStorage(str(file_path))

        # Touch the file so os.path.exists passes in read()
        file_path.touch()

        assert storage.read() == [{"AAPL": {}}]

    @patch("builtins.open", new_callable=mock_open, read_data="{ bad json")
    def test_read_failure_mocked_decode_error(self, _mock_file, tmp_path):
        """Test method."""
        file_path = tmp_path / "mocked_fail.json"
        storage = JsonStatsStorage(str(file_path))
        file_path.touch()

class TestJsonStatsStorageWrite:
    """
    Explicit test class to comprehensively test the JsonStatsStorage.write method
    error handling and atomic replacement properties.
    """
    def test_write_json_dump_error(self, tmp_path):
        """Test method."""
        file_path = tmp_path / "stats.json"
        storage = JsonStatsStorage(str(file_path))

        # Object that cannot be serialized by json.dump
        class UnserializableObject:
            """Unserializable."""
            pass

        data = [{"TICKER": UnserializableObject()}]

        with pytest.raises(TypeError):
            storage.write(data)

        # The temporary file should have been cleaned up after dump failure
        temp_path = str(file_path) + '.tmp'
        assert not os.path.exists(temp_path)

        # Original file should be untouched and read validly (as [])
        assert not storage.read()

    def test_write_os_replace_error_cleanup(self, tmp_path):
        """Test method."""
        file_path = tmp_path / "stats.json"
        storage = JsonStatsStorage(str(file_path))
        data = [{"TICKER": {"date-begin": "2023-01-01", "date-end": "2023-12-31"}}]

        with patch("os.replace", side_effect=OSError("Mocked OS Error")):
            with pytest.raises(OSError, match="Mocked OS Error"):
                storage.write(data)

        # Temp file should be removed in the except block
        temp_path = str(file_path) + '.tmp'
        assert not os.path.exists(temp_path)

        # Original file should remain uncorrupted (as an empty list since it was initialized)
        assert not storage.read()

    def test_write_os_replace_error_temp_cleanup_explicit(self, tmp_path):
        """Test method."""
        file_path = tmp_path / "stats_error.json"
        storage = JsonStatsStorage(str(file_path))
        data = [{"TICKER": {"date-begin": "2023-01-01", "date-end": "2023-12-31"}}]
        with patch("os.replace", side_effect=Exception("Mocked error")):
            with pytest.raises(Exception, match="Mocked error"):
                storage.write(data)
        assert not os.path.exists(str(file_path) + '.tmp')

class TestJsonStatsStorageReadAdditional:
    """Test class."""
    def test_json_stats_storage_read_success(self, tmp_path):
        """Test method."""
        file_path = tmp_path / "success.json"
        storage = JsonStatsStorage(str(file_path))
        data = [{"TICKER": {"date-begin": "2023-01-01"}}]
        with open(file_path, "w", encoding='utf-8') as f:
            json.dump(data, f)
        assert storage.read() == data

    def test_json_stats_storage_read_failure_decode(self, tmp_path):
        """Test method."""
        file_path = tmp_path / "failure.json"
        storage = JsonStatsStorage(str(file_path))
        with open(file_path, "w", encoding='utf-8') as f:
            f.write("{invalid json")
        assert not storage.read()

    def test_json_stats_storage_read_file_not_exists(self, tmp_path):
        """Test method."""
        file_path = tmp_path / "not_exists.json"
        storage = JsonStatsStorage(str(file_path))
        if os.path.exists(str(file_path)):
            os.remove(str(file_path))
        assert not storage.read()

    def test_json_stats_storage_read_not_a_list(self, tmp_path):
        """Test method."""
        file_path = tmp_path / "not_list.json"
        storage = JsonStatsStorage(str(file_path))
        with open(file_path, "w", encoding='utf-8') as f:
            json.dump({"not": "a list"}, f)
        assert not storage.read()

class TestJsonStatsStorageReadMethod:
    """
    Explicit test class to comprehensively test the JsonStatsStorage.read method
    as requested: asserting empty lists are returned on failure and valid data
    is returned on success, using mocked open() or temporary directories.
    """

    def test_read_success_valid_data(self, tmp_path):
        """Test method."""
        file_path = tmp_path / "valid.json"
        storage = JsonStatsStorage(str(file_path))
        valid_data = [{"AAPL": {"date-begin": "2023-01-01"}}]

        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(valid_data, f)

        assert storage.read() == valid_data

    def test_read_failure_file_not_exists(self, tmp_path):
        """Test method."""
        file_path = tmp_path / "not_exists.json"
        storage = JsonStatsStorage(str(file_path))
        # Ensure it's deleted after init
        if os.path.exists(str(file_path)):
            os.remove(str(file_path))

        assert not storage.read()

    def test_read_failure_malformed_json(self, tmp_path):
        """Test method."""
        file_path = tmp_path / "malformed.json"
        storage = JsonStatsStorage(str(file_path))

        with open(file_path, 'w', encoding='utf-8') as f:
            f.write("{ invalid_json }")

        assert not storage.read()

    def test_read_failure_not_a_list(self, tmp_path):
        """Test method."""
        file_path = tmp_path / "not_list.json"
        storage = JsonStatsStorage(str(file_path))

        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump({"not": "a list"}, f)

        assert not storage.read()

    @patch("builtins.open", new_callable=mock_open, read_data="[{\"AAPL\": {}}]")
    def test_read_success_mocked(self, _mock_file, tmp_path):
        """Test method."""
        file_path = tmp_path / "mocked_success.json"
        storage = JsonStatsStorage(str(file_path))

        # Touch the file so os.path.exists passes in read()
        file_path.touch()

        assert storage.read() == [{"AAPL": {}}]

    @patch("builtins.open", new_callable=mock_open, read_data="{ bad json")
    def test_read_failure_mocked_decode_error(self, _mock_file, tmp_path):
        """Test method."""
        file_path = tmp_path / "mocked_fail.json"
        storage = JsonStatsStorage(str(file_path))
        file_path.touch()

        assert not storage.read()

class TestJsonStatsStorageWriteError:
    """
    Explicit test class to cover the error path for JsonStatsStorage write method.
    """
    def test_write_os_replace_exception_cleanup(self, tmp_path):
        """Test method."""
        file_path = tmp_path / "test_write.json"
        storage = JsonStatsStorage(str(file_path))
        data = [{"TICKER": {"date-begin": "2023-01-01"}}]

        with patch('os.replace', side_effect=OSError("Mocked error")):
            with pytest.raises(OSError, match="Mocked error"):
                storage.write(data)

        temp_path = str(file_path) + '.tmp'
        assert not os.path.exists(temp_path)

    def test_write_json_dump_exception_cleanup(self, tmp_path):
        """Test method."""
        file_path = tmp_path / "test_write.json"
        storage = JsonStatsStorage(str(file_path))

        class Unserializable:
            """Unserializable."""
            pass

        data = [{"TICKER": Unserializable()}]

        with pytest.raises(TypeError):
            storage.write(data)

        temp_path = str(file_path) + '.tmp'
        assert not os.path.exists(temp_path)

class TestJsonStatsStorageWriteErrorPath:
    """Test class."""
    def test_write_os_replace_exception_removes_temp_file(self, tmp_path):
        """Test method."""
        file_path = tmp_path / "stats.json"
        storage = JsonStatsStorage(str(file_path))
        data = [{"TICKER": {"date-begin": "2024-01-01"}}]

        with patch("os.replace", side_effect=OSError("Failed to replace")):
            with pytest.raises(OSError, match="Failed to replace"):
                storage.write(data)

        assert not os.path.exists(str(file_path) + ".tmp")

class TestJsonStatsStorageReadFinal:
    """
    Final test class to assert empty lists are returned on failure and valid data
    is returned on success for JsonStatsStorage.read method.
    """
    def test_read_returns_valid_data_on_success(self, tmp_path):
        """Test method."""
        file_path = tmp_path / "valid_data.json"
        storage = JsonStatsStorage(str(file_path))
        data = [{"AAPL": {"profit": 100}}]
        with open(file_path, "w", encoding='utf-8') as f:
            json.dump(data, f)

        assert storage.read() == data

    def test_read_returns_empty_list_on_file_not_found(self, tmp_path):
        """Test method."""
        file_path = tmp_path / "missing_file.json"
        storage = JsonStatsStorage(str(file_path))
        if os.path.exists(str(file_path)):
            os.remove(str(file_path))

        assert not storage.read()

    def test_read_returns_empty_list_on_invalid_json(self, tmp_path):
        """Test method."""
        file_path = tmp_path / "invalid_json.json"
        storage = JsonStatsStorage(str(file_path))
        with open(file_path, "w", encoding='utf-8') as f:
            f.write("{invalid json")

        assert not storage.read()

    def test_read_returns_empty_list_on_non_list_data(self, tmp_path):
        """Test method."""
        file_path = tmp_path / "non_list.json"
        storage = JsonStatsStorage(str(file_path))
        data = {"AAPL": {"profit": 100}}
        with open(file_path, "w", encoding='utf-8') as f:
            json.dump(data, f)

        assert not storage.read()

    @patch("builtins.open", new_callable=mock_open, read_data='[{"MSFT": {"profit": 50}}]')
    def test_read_returns_valid_data_on_success_mocked(self, _mock_file, tmp_path):
        """Test method."""
        file_path = tmp_path / "mock_valid_data.json"
        storage = JsonStatsStorage(str(file_path))
        file_path.touch()

        assert storage.read() == [{"MSFT": {"profit": 50}}]

    @patch("builtins.open", new_callable=mock_open, read_data="{invalid json")
    def test_read_returns_empty_list_on_invalid_json_mocked(self, _mock_file, tmp_path):
        """Test method."""
        file_path = tmp_path / "mock_invalid_json.json"
        storage = JsonStatsStorage(str(file_path))
        file_path.touch()

        assert not storage.read()

class TestJsonStatsStorageReadAdditionalTests:
    """
    Additional tests for JsonStatsStorage read method to satisfy the specific issue request.
    """
    def test_read_returns_empty_list_on_file_not_found_extra(self, tmp_path):
        """Test method."""
        file_path = tmp_path / "does_not_exist.json"
        storage = JsonStatsStorage(str(file_path))
        if os.path.exists(str(file_path)):
            os.remove(str(file_path))
        assert not storage.read()

    def test_read_returns_empty_list_on_json_decode_error_extra(self, tmp_path):
        """Test method."""
        file_path = tmp_path / "bad.json"
        storage = JsonStatsStorage(str(file_path))
        with open(file_path, "w", encoding='utf-8') as f:
            f.write("definitely not json")
        assert not storage.read()

    def test_read_returns_empty_list_on_non_list_type_extra(self, tmp_path):
        """Test method."""
        file_path = tmp_path / "dict.json"
        storage = JsonStatsStorage(str(file_path))
        with open(file_path, "w", encoding='utf-8') as f:
            json.dump({"i_am": "a dictionary"}, f)
        assert not storage.read()

    def test_read_returns_valid_data_on_success_extra(self, tmp_path):
        """Test method."""
        file_path = tmp_path / "good.json"
        storage = JsonStatsStorage(str(file_path))
        data = [{"TEST": {"metric": 123}}]
        with open(file_path, "w", encoding='utf-8') as f:
            json.dump(data, f)
        assert storage.read() == data

class TestJsonStatsStorageReadMethodIssue:
    """
    Tests for JsonStatsStorage read method to assert empty lists are returned on failure
    and valid data is returned on success.
    """
    def test_read_returns_empty_list_when_file_does_not_exist(self, tmp_path):
        """Test method."""
        file_path = tmp_path / "missing.json"
        storage = JsonStatsStorage(str(file_path))
        if os.path.exists(str(file_path)):
            os.remove(str(file_path))
        assert not storage.read()

    def test_read_returns_valid_data_on_success(self, tmp_path):
        """Test method."""
        file_path = tmp_path / "valid.json"
        storage = JsonStatsStorage(str(file_path))
        data = [{"TEST": {"metric": 1}}]
        with open(file_path, "w", encoding='utf-8') as f:
            json.dump(data, f)
        assert storage.read() == data

    def test_read_returns_empty_list_on_invalid_json(self, tmp_path):
        """Test method."""
        file_path = tmp_path / "invalid.json"
        storage = JsonStatsStorage(str(file_path))
        with open(file_path, "w", encoding='utf-8') as f:
            f.write("{invalid json")
        assert not storage.read()

    def test_read_returns_empty_list_on_non_list_data(self, tmp_path):
        """Test method."""
        file_path = tmp_path / "non_list.json"
        storage = JsonStatsStorage(str(file_path))
        with open(file_path, "w", encoding='utf-8') as f:
            json.dump({"not": "a list"}, f)
        assert not storage.read()

    @patch("builtins.open", new_callable=mock_open, read_data="[{\"TEST\": 1}]")
    def test_read_success_mocked_open(self, _mock_file, tmp_path):
        """Test method."""
        file_path = tmp_path / "mocked.json"
        storage = JsonStatsStorage(str(file_path))
        file_path.touch()
        assert storage.read() == [{"TEST": 1}]

    @patch("builtins.open", new_callable=mock_open, read_data="{invalid")
    def test_read_invalid_json_mocked_open(self, _mock_file, tmp_path):
        """Test method."""
        file_path = tmp_path / "mocked_fail.json"
        storage = JsonStatsStorage(str(file_path))
        file_path.touch()
        assert not storage.read()

class TestJsonStatsStorageReadMissingTests:
    """
    Tests for JsonStatsStorage read method to assert empty lists are returned on failure
    and valid data is returned on success. Added as requested.
    """
    def test_read_success_valid_data(self, tmp_path):
        """Test method."""
        file_path = tmp_path / "valid.json"
        storage = JsonStatsStorage(str(file_path))
        data = [{"TEST": {"metric": 1}}]
        with open(file_path, "w", encoding='utf-8') as f:
            json.dump(data, f)
        assert storage.read() == data

    def test_read_failure_file_missing(self, tmp_path):
        """Test method."""
        file_path = tmp_path / "missing.json"
        storage = JsonStatsStorage(str(file_path))
        if os.path.exists(str(file_path)):
            os.remove(str(file_path))
        assert not storage.read()

    def test_read_failure_malformed_json(self, tmp_path):
        """Test method."""
        file_path = tmp_path / "malformed.json"
        storage = JsonStatsStorage(str(file_path))
        with open(file_path, "w", encoding='utf-8') as f:
            f.write("{invalid json")
        assert not storage.read()

    def test_read_failure_non_list_type(self, tmp_path):
        """Test method."""
        file_path = tmp_path / "non_list.json"
        storage = JsonStatsStorage(str(file_path))
        with open(file_path, "w", encoding='utf-8') as f:
            json.dump({"not": "a list"}, f)
        assert not storage.read()

class TestJsonStatsStorageReadMissingCoverage:
    """
    Tests for JsonStatsStorage read method to assert empty lists are returned on failure
    and valid data is returned on success. Added to resolve the specific testing gap.
    """
    def test_read_returns_valid_data_on_success(self, tmp_path):
        """Test method."""
        file_path = tmp_path / "valid.json"
        storage = JsonStatsStorage(str(file_path))
        data = [{"TEST": {"metric": 1}}]
        with open(file_path, "w", encoding='utf-8') as f:
            json.dump(data, f)
        assert storage.read() == data

    def test_read_returns_empty_list_when_file_does_not_exist(self, tmp_path):
        """Test method."""
        file_path = tmp_path / "missing.json"
        storage = JsonStatsStorage(str(file_path))
        if os.path.exists(str(file_path)):
            os.remove(str(file_path))
        assert not storage.read()

    def test_read_returns_empty_list_on_malformed_json(self, tmp_path):
        """Test method."""
        file_path = tmp_path / "malformed.json"
        storage = JsonStatsStorage(str(file_path))
        with open(file_path, "w", encoding='utf-8') as f:
            f.write("{invalid json")
        assert not storage.read()

    def test_read_returns_empty_list_when_data_is_not_a_list(self, tmp_path):
        """Test method."""
        file_path = tmp_path / "non_list.json"
        storage = JsonStatsStorage(str(file_path))
        with open(file_path, "w", encoding='utf-8') as f:
            json.dump({"not": "a list"}, f)
        assert not storage.read()

class TestJsonStatsStorageReadMethodIssueNew:
    """Test class."""
    def test_read_returns_valid_data_on_success_with_tmp_path(self, tmp_path):
        """Test method."""
        file_path = tmp_path / "data.json"
        storage = JsonStatsStorage(str(file_path))
        data = [{"TEST": {"metric": 1}}]
        with open(file_path, "w", encoding='utf-8') as f:
            json.dump(data, f)
        assert storage.read() == data

    def test_read_returns_empty_list_when_file_does_not_exist_with_tmp_path(self, tmp_path):
        """Test method."""
        file_path = tmp_path / "missing.json"
        storage = JsonStatsStorage(str(file_path))
        if os.path.exists(str(file_path)):
            os.remove(str(file_path))
        assert not storage.read()

    def test_read_returns_empty_list_on_invalid_json_with_tmp_path(self, tmp_path):
        """Test method."""
        file_path = tmp_path / "invalid.json"
        storage = JsonStatsStorage(str(file_path))
        with open(file_path, "w", encoding='utf-8') as f:
            f.write("{invalid json")
        assert not storage.read()

    def test_read_returns_empty_list_on_non_list_data_with_tmp_path(self, tmp_path):
        """Test method."""
        file_path = tmp_path / "non_list.json"
        storage = JsonStatsStorage(str(file_path))
        with open(file_path, "w", encoding='utf-8') as f:
            json.dump({"not": "a list"}, f)
        assert not storage.read()

class TestJsonStatsStorageReadMissingCoverageAdded:
    """
    Explicit test to assert empty lists are returned on failure and valid data
    is returned on success for JsonStatsStorage.read method.
    """
    def test_read_returns_empty_list_when_file_does_not_exist(self, tmp_path):
        """Test method."""
        file_path = tmp_path / "missing.json"
        storage = JsonStatsStorage(str(file_path))
        if os.path.exists(str(file_path)):
            os.remove(str(file_path))
        assert not storage.read()

    def test_read_returns_valid_data_on_success(self, tmp_path):
        """Test method."""
        file_path = tmp_path / "valid.json"
        storage = JsonStatsStorage(str(file_path))
        data = [{"TEST": {"metric": 1}}]
        with open(file_path, "w", encoding='utf-8') as f:
            json.dump(data, f)
        assert storage.read() == data

    def test_read_returns_empty_list_on_invalid_json(self, tmp_path):
        """Test method."""
        file_path = tmp_path / "invalid.json"
        storage = JsonStatsStorage(str(file_path))
        with open(file_path, "w", encoding='utf-8') as f:
            f.write("{invalid json")
        assert not storage.read()

    def test_read_returns_empty_list_on_non_list_data(self, tmp_path):
        """Test method."""
        file_path = tmp_path / "non_list.json"
        storage = JsonStatsStorage(str(file_path))
        with open(file_path, "w", encoding='utf-8') as f:
            json.dump({"not": "a list"}, f)
        assert not storage.read()

def test_stats_manager_save_stats_batch(tmp_path):
    """Test stats manager save batch."""
    StatsManager._instance = None  # pylint: disable=protected-access
    file_path = tmp_path / "stats.json"
    storage = JsonStatsStorage(str(file_path))
    manager = StatsManager(storage)

    # Initial batch save
    batch1 = [
        {
            "ticker": "AAPL",
            "date_begin": "2023-01-01",
            "date_end": "2023-12-31",
            "strategies_metrics": {"SMA": {"profit": 100}}
        },
        {
            "ticker": "MSFT",
            "date_begin": "2023-01-01",
            "date_end": "2023-12-31",
            "strategies_metrics": {"EMA": {"profit": 50}}
        }
    ]
    manager.save_stats_batch(batch1)

    data = storage.read()
    assert len(data) == 2

    # Create dict for easy assertion
    data_dict = {}
    for entry in data:
        for k, v in entry.items():
            data_dict[k] = v

    assert "AAPL" in data_dict
    assert "MSFT" in data_dict
    assert data_dict["AAPL"]["SMA"]["profit"] == 100
    assert data_dict["MSFT"]["EMA"]["profit"] == 50

    # Update and append new in batch
    batch2 = [
        {
            "ticker": "AAPL",
            "date_begin": "2023-01-01",
            "date_end": "2024-01-01", # different date, should update
            "strategies_metrics": {"SMA": {"profit": 200}}
        },
        {
            "ticker": "MSFT",
            "date_begin": "2023-01-01",
            "date_end": "2023-12-31", # same date, should do nothing
            "strategies_metrics": {"EMA": {"profit": 999}}
        },
        {
            "ticker": "TSLA", # new ticker, should append
            "date_begin": "2024-01-01",
            "date_end": "2024-12-31",
            "strategies_metrics": {"RSI": {"profit": 300}}
        }
    ]
    manager.save_stats_batch(batch2)

    data = storage.read()
    assert len(data) == 3

    data_dict = {}
    for entry in data:
        for k, v in entry.items():
            data_dict[k] = v

    assert data_dict["AAPL"]["SMA"]["profit"] == 200 # updated
    assert data_dict["MSFT"]["EMA"]["profit"] == 50 # not updated
    assert "TSLA" in data_dict
    assert data_dict["TSLA"]["RSI"]["profit"] == 300
