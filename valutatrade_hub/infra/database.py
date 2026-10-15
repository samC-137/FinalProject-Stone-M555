import json
import os
import tempfile
from copy import deepcopy
from pathlib import Path
from typing import Any


class DatabaseManager:
    """Единая точка чтения и записи JSON-файлов проекта."""

    _instance: "DatabaseManager | None" = None
    _files = {
        "users.json",
        "portfolios.json",
        "rates.json",
        "exchange_rates.json",
    }

    def __new__(cls) -> "DatabaseManager":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self) -> None:
        if hasattr(self, "_data_dir"):
            return
        self._data_dir = Path(__file__).resolve().parents[2] / "data"
        self._data_dir.mkdir(parents=True, exist_ok=True)

    def _get_path(self, filename: str) -> Path:
        if filename not in self._files:
            raise ValueError(f"Файл '{filename}' не поддерживается")
        return self._data_dir / filename

    def read_json(self, filename: str, default: Any = None) -> Any:
        """Прочитать JSON-файл или вернуть значение по умолчанию."""
        path = self._get_path(filename)
        if not path.exists():
            return deepcopy(default)

        try:
            with path.open(encoding="utf-8") as file:
                return json.load(file)
        except json.JSONDecodeError as error:
            raise ValueError(f"Файл '{filename}' содержит некорректный JSON") from error

    def write_json(self, filename: str, data: Any) -> None:
        """Атомарно записать данные в JSON-файл."""
        path = self._get_path(filename)
        temporary_path: str | None = None
        try:
            with tempfile.NamedTemporaryFile(
                mode="w",
                encoding="utf-8",
                dir=path.parent,
                prefix=f".{filename}.",
                suffix=".tmp",
                delete=False,
            ) as temporary_file:
                temporary_path = temporary_file.name
                json.dump(data, temporary_file, ensure_ascii=False, indent=2)
                temporary_file.write("\n")
                temporary_file.flush()
                os.fsync(temporary_file.fileno())
            os.replace(temporary_path, path)
        finally:
            if temporary_path is not None and os.path.exists(temporary_path):
                os.unlink(temporary_path)

    def load_users(self) -> list[dict[str, Any]]:
        """Загрузить пользователей."""
        return self.read_json("users.json", [])

    def save_users(self, users: list[dict[str, Any]]) -> None:
        """Сохранить пользователей."""
        self.write_json("users.json", users)

    def load_portfolios(self) -> list[dict[str, Any]]:
        """Загрузить портфели."""
        return self.read_json("portfolios.json", [])

    def save_portfolios(self, portfolios: list[dict[str, Any]]) -> None:
        """Сохранить портфели."""
        self.write_json("portfolios.json", portfolios)

    def load_rates(self) -> dict[str, Any]:
        """Загрузить последние курсы."""
        return self.read_json("rates.json", {"pairs": {}, "last_refresh": None})

    def save_rates(self, rates: dict[str, Any]) -> None:
        """Сохранить последние курсы."""
        self.write_json("rates.json", rates)

    def load_exchange_rates(self) -> list[dict[str, Any]]:
        """Загрузить историю курсов."""
        return self.read_json("exchange_rates.json", [])

    def save_exchange_rates(self, history: list[dict[str, Any]]) -> None:
        """Сохранить историю курсов."""
        self.write_json("exchange_rates.json", history)
