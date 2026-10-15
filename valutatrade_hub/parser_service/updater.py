import logging
from datetime import datetime, timezone
from typing import Any

from valutatrade_hub.core.exceptions import ApiRequestError
from valutatrade_hub.parser_service.api_clients import (
    BaseApiClient,
    CoinGeckoClient,
    ExchangeRateApiClient,
)
from valutatrade_hub.parser_service.config import ParserConfig
from valutatrade_hub.parser_service.storage import RatesStorage


class RatesUpdater:
    """Получает курсы из источников и обновляет локальные файлы."""

    def __init__(
        self,
        clients: list[BaseApiClient] | None = None,
        storage: RatesStorage | None = None,
        config: ParserConfig | None = None,
    ) -> None:
        self.config = config or ParserConfig()
        self.clients = clients or [
            CoinGeckoClient(self.config),
            ExchangeRateApiClient(self.config),
        ]
        self.storage = storage or RatesStorage()
        self.logger = logging.getLogger(__name__)

    def run_update(self, sources: set[str] | None = None) -> dict[str, Any]:
        """Обновить данные от выбранных источников."""
        self.logger.info("Starting rates update")
        updated_rates: dict[str, dict[str, Any]] = {}
        errors: list[str] = []

        for client in self.clients:
            source_key = _source_key(client.source)
            if sources and source_key not in sources:
                continue
            try:
                rates = client.fetch_rates()
            except ApiRequestError as error:
                self.logger.error("Failed to fetch from %s: %s", client.source, error)
                errors.append(str(error))
                continue
            updated_rates.update(rates)
            self.logger.info("Fetched %s rates from %s", len(rates), client.source)

        if not updated_rates:
            return {
                "updated": 0,
                "errors": errors,
                "last_refresh": None,
            }

        count = self.storage.save_updates(updated_rates)
        last_refresh = datetime.now(timezone.utc).isoformat()
        self.logger.info("Rates update finished: %s rates saved", count)
        return {
            "updated": count,
            "errors": errors,
            "last_refresh": last_refresh,
        }


def _source_key(source: str) -> str:
    if source == "CoinGecko":
        return "coingecko"
    if source == "ExchangeRate-API":
        return "exchangerate"
    return source.lower()
