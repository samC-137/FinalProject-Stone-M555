import tempfile
import unittest
from pathlib import Path

from valutatrade_hub.infra.database import DatabaseManager
from valutatrade_hub.infra.settings import SettingsLoader
from valutatrade_hub.parser_service.config import ParserConfig


class TestDataDirectory(unittest.TestCase):
    def test_settings_resolve_data_directory(self) -> None:
        settings = SettingsLoader()
        original = settings._settings
        with tempfile.TemporaryDirectory() as directory:
            settings._settings = {"data_dir": directory}
            try:
                self.assertEqual(settings.get_data_dir(), Path(directory).resolve())
            finally:
                settings._settings = original

    def test_database_can_use_configured_data_directory(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            database = DatabaseManager(data_dir=Path(directory))
            database.save_users([{"username": "test"}])

            self.assertEqual(database.load_users(), [{"username": "test"}])
            self.assertTrue((Path(directory) / "users.json").exists())

    def test_default_storage_paths_use_project_setting(self) -> None:
        settings = SettingsLoader()
        original_settings = settings._settings
        original_database = DatabaseManager._instance
        with tempfile.TemporaryDirectory() as directory:
            settings._settings = {"data_dir": directory}
            DatabaseManager._instance = None
            try:
                expected_path = Path(directory).resolve()
                self.assertEqual(DatabaseManager()._data_dir, expected_path)
                self.assertEqual(ParserConfig().DATA_DIR, expected_path)
            finally:
                settings._settings = original_settings
                DatabaseManager._instance = original_database
