from datetime import datetime, timezone
from typing import Any

from valutatrade_hub.core.currencies import CryptoCurrency, get_currency
from valutatrade_hub.core.exceptions import CurrencyNotFoundError
from valutatrade_hub.core.usecases import get_rate
from valutatrade_hub.infra.database import DatabaseManager


class RatesStorage:
    """Сохраняет текущие курсы и историю обновлений."""

    def __init__(self, database: DatabaseManager | None = None) -> None:
        self.database = database or DatabaseManager()

    def save_updates(self, updates: dict[str, dict[str, Any]]) -> int:
        """Обновить кэш и добавить новые значения в историю."""
        cache = self.database.load_rates()
        pairs = cache.setdefault("pairs", {})
        history = self.database.load_exchange_rates()
        history_ids = {item.get("id") for item in history if isinstance(item, dict)}
        count = 0

        for pair, value in updates.items():
            candidate_time = _parse_timestamp(value["updated_at"])
            current = pairs.get(pair)
            if isinstance(current, dict) and current.get("updated_at"):
                if _parse_timestamp(current["updated_at"]) >= candidate_time:
                    continue

            pairs[pair] = value
            record_id = f"{pair}_{value['updated_at']}"
            if record_id not in history_ids:
                from_code, to_code = pair.split("_", maxsplit=1)
                history.append(
                    {
                        "id": record_id,
                        "from_currency": from_code,
                        "to_currency": to_code,
                        "rate": value["rate"],
                        "timestamp": value["updated_at"],
                        "source": value["source"],
                        "meta": value.get("meta", {}),
                    }
                )
                history_ids.add(record_id)
            count += 1

        if count:
            cache["last_refresh"] = datetime.now(timezone.utc).isoformat()
            self.database.save_rates(cache)
            self.database.save_exchange_rates(history)
        return count

    def list_rates(
        self,
        currency: str | None = None,
        top: int | None = None,
        base: str = "USD",
    ) -> list[dict[str, Any]]:
        """Подготовить курсы для показа и применить фильтры."""
        cache = self.database.load_rates()
        pairs = cache.get("pairs", {})
        if not pairs:
            return []
        base_code = get_currency(base).code
        currency_code = get_currency(currency).code if currency else None
        rows: list[dict[str, Any]] = []

        for pair, value in pairs.items():
            from_code, to_code = pair.split("_", maxsplit=1)
            asset_code = to_code if from_code == base_code else from_code
            if currency_code and currency_code not in {from_code, to_code}:
                continue
            if top is not None:
                try:
                    is_crypto = isinstance(get_currency(asset_code), CryptoCurrency)
                except CurrencyNotFoundError:
                    is_crypto = False
                if not is_crypto:
                    continue

            rate_info = get_rate(asset_code, base_code, self.database)
            shown_pair = f"{asset_code}_{base_code}"

            rows.append(
                {
                    "pair": shown_pair,
                    "rate": rate_info["rate"],
                    "updated_at": rate_info["updated_at"],
                    "source": rate_info["source"],
                    "currency": asset_code,
                }
            )

        if top is not None:
            rows.sort(key=lambda item: item["rate"], reverse=True)
            rows = rows[:top]
        else:
            rows.sort(key=lambda item: item["pair"])
        return rows


def _parse_timestamp(value: str) -> datetime:
    timestamp = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if timestamp.tzinfo is None:
        timestamp = timestamp.replace(tzinfo=timezone.utc)
    return timestamp
