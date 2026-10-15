import unittest
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

from valutatrade_hub.core.exceptions import ApiRequestError
from valutatrade_hub.core.usecases import get_rate


class TestRateRefresh(unittest.TestCase):
    def setUp(self) -> None:
        self.database = _FakeDatabase()
        self.settings = _FakeSettings()

    def test_refreshes_when_rate_is_missing(self) -> None:
        updated_at = datetime.now(timezone.utc).isoformat()
        updater = _FakeUpdater(
            self.database,
            {"BTC_USD": _rate(82000, updated_at, "CoinGecko")},
        )

        with patch(
            "valutatrade_hub.parser_service.updater.RatesUpdater",
            return_value=updater,
        ) as updater_class:
            result = get_rate("BTC", "USD", self.database, self.settings)

        self.assertEqual(result["rate"], 82000)
        self.assertEqual(result["source"], "CoinGecko")
        updater_class.assert_called_once()
        self.assertIs(updater_class.call_args.kwargs["storage"].database, self.database)

    def test_refreshes_when_rate_is_stale(self) -> None:
        old_time = (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat()
        fresh_time = datetime.now(timezone.utc).isoformat()
        self.database.rates = {
            "pairs": {"BTC_USD": _rate(80000, old_time, "CoinGecko")}
        }
        updater = _FakeUpdater(
            self.database,
            {"BTC_USD": _rate(82000, fresh_time, "CoinGecko")},
        )

        with patch(
            "valutatrade_hub.parser_service.updater.RatesUpdater",
            return_value=updater,
        ) as updater_class:
            result = get_rate("BTC", "USD", self.database, self.settings)

        self.assertEqual(result["rate"], 82000)
        updater_class.assert_called_once()
        self.assertIs(updater_class.call_args.kwargs["storage"].database, self.database)

    def test_reports_refresh_failure_without_hiding_manual_command(self) -> None:
        updater = _FakeUpdater(self.database, {}, errors=["CoinGecko: HTTP 503"])

        with patch(
            "valutatrade_hub.parser_service.updater.RatesUpdater",
            return_value=updater,
        ):
            with self.assertRaises(ApiRequestError) as context:
                get_rate("BTC", "USD", self.database, self.settings)

        self.assertIn("HTTP 503", str(context.exception))
        self.assertIn("update-rates", str(context.exception))


class _FakeDatabase:
    def __init__(self) -> None:
        self.rates = {"pairs": {}}

    def load_rates(self) -> dict[str, object]:
        return self.rates

    def save_rates(self, rates: dict[str, object]) -> None:
        self.rates = rates


class _FakeSettings:
    def get(self, key: str, default: int | None = None) -> int | None:
        return default


class _FakeUpdater:
    def __init__(
        self,
        database: _FakeDatabase,
        updates: dict[str, dict[str, object]],
        errors: list[str] | None = None,
    ) -> None:
        self.database = database
        self.updates = updates
        self.errors = errors or []

    def run_update(self) -> dict[str, object]:
        self.database.save_rates({"pairs": self.updates})
        return {
            "updated": len(self.updates),
            "errors": self.errors,
            "last_refresh": datetime.now(timezone.utc).isoformat(),
        }


def _rate(value: float, updated_at: str, source: str) -> dict[str, object]:
    return {"rate": value, "updated_at": updated_at, "source": source}


if __name__ == "__main__":
    unittest.main()
