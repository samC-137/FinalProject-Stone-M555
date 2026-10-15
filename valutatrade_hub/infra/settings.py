import tomllib
from pathlib import Path
from typing import Any


class SettingsLoader:
    """Один экземпляр настроек проекта."""

    _instance: "SettingsLoader | None" = None

    def __new__(cls) -> "SettingsLoader":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self) -> None:
        if hasattr(self, "_settings"):
            return
        config_path = Path(__file__).resolve().parents[2] / "pyproject.toml"
        with config_path.open("rb") as config_file:
            project_config = tomllib.load(config_file)
        self._settings = project_config.get("tool", {}).get("valutatrade", {})

    def get(self, key: str, default: Any = None) -> Any:
        """Получить значение настройки."""
        return self._settings.get(key, default)

    def get_data_dir(self) -> Path:
        """Вернуть абсолютный путь к каталогу данных проекта."""
        project_root = Path(__file__).resolve().parents[2]
        data_dir = Path(self.get("data_dir", "data"))
        if not data_dir.is_absolute():
            data_dir = project_root / data_dir
        return data_dir.resolve()
