from abc import ABC, abstractmethod
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from math import isfinite
from typing import Any

import requests

from valutatrade_hub.core.exceptions import ApiRequestError
from valutatrade_hub.parser_service.config import ParserConfig


class BaseApiClient(ABC):
    """Общий интерфейс клиента источника курсов."""

    source = "API"

    def __init__(self, config: ParserConfig | None = None) -> None:
        self.config = config or ParserConfig()

    @abstractmethod
    def fetch_rates(self) -> dict[str, dict[str, Any]]:
        """Получить курсы в общем формате приложения."""

    def _get_json(
        self,
        url: str,
        params: dict[str, str] | None = None,
        headers: dict[str, str] | None = None,
    ) -> tuple[Any, int]:
        try:
            response = requests.get(
                url,
                params=params,
                headers=headers,
                timeout=self.config.REQUEST_TIMEOUT,
            )
        except requests.exceptions.RequestException as error:
            raise ApiRequestError(
                f"{self.source}: ошибка сети ({type(error).__name__})"
            ) from error

        if response.status_code != 200:
            explanation = _http_error_message(response.status_code)
            raise ApiRequestError(f"{self.source}: {explanation}")

        try:
            return response.json(), response.status_code
        except ValueError as error:
            raise ApiRequestError(f"{self.source}: ответ не является JSON") from error


class CoinGeckoClient(BaseApiClient):
    """Получает курсы криптовалют в долларах."""

    source = "CoinGecko"

    def fetch_rates(self) -> dict[str, dict[str, Any]]:
        ids = ",".join(self.config.CRYPTO_ID_MAP.values())
        headers = (
            {"x-cg-demo-api-key": self.config.COINGECKO_API_KEY}
            if self.config.COINGECKO_API_KEY
            else None
        )
        payload, status_code = self._get_json(
            self.config.COINGECKO_URL,
            {"ids": ids, "vs_currencies": self.config.BASE_CURRENCY.lower()},
            headers,
        )
        if not isinstance(payload, dict):
            raise ApiRequestError("CoinGecko: ответ имеет неверный формат")

        now = datetime.now(timezone.utc).isoformat()
        rates: dict[str, dict[str, Any]] = {}
        for code, coin_id in self.config.CRYPTO_ID_MAP.items():
            coin_data = payload.get(coin_id)
            rate = (
                coin_data.get(self.config.BASE_CURRENCY.lower())
                if isinstance(coin_data, dict)
                else None
            )
            if not _valid_rate(rate):
                continue
            rates[f"{code}_{self.config.BASE_CURRENCY}"] = {
                "rate": float(rate),
                "updated_at": now,
                "source": self.source,
                "meta": {"raw_id": coin_id, "status_code": status_code},
            }
        if not rates:
            raise ApiRequestError("CoinGecko: в ответе нет корректных курсов")
        return rates


class ExchangeRateApiClient(BaseApiClient):
    """Получает курсы фиатных валют."""

    source = "ExchangeRate-API"

    def fetch_rates(self) -> dict[str, dict[str, Any]]:
        api_key = self.config.EXCHANGERATE_API_KEY
        if not api_key:
            raise ApiRequestError(
                "ExchangeRate-API: задайте переменную EXCHANGERATE_API_KEY"
            )

        url = (
            f"{self.config.EXCHANGERATE_API_URL.rstrip('/')}/"
            f"{api_key}/latest/{self.config.BASE_CURRENCY}"
        )
        payload, status_code = self._get_json(url)
        if not isinstance(payload, dict) or payload.get("result") != "success":
            error_type = (
                payload.get("error-type", "неизвестная ошибка")
                if isinstance(payload, dict)
                else "неверный ответ"
            )
            raise ApiRequestError(f"ExchangeRate-API: {error_type}")

        raw_rates = payload.get("conversion_rates") or payload.get("rates", {})
        if not isinstance(raw_rates, dict):
            raise ApiRequestError(
                "ExchangeRate-API: список курсов имеет неверный формат"
            )

        updated_at = _parse_exchange_timestamp(payload.get("time_last_update_utc"))
        rates: dict[str, dict[str, Any]] = {}
        for code in self.config.FIAT_CURRENCIES:
            rate_from_usd = raw_rates.get(code)
            if not _valid_rate(rate_from_usd):
                continue
            rates[f"{code}_{self.config.BASE_CURRENCY}"] = {
                "rate": 1 / float(rate_from_usd),
                "updated_at": updated_at,
                "source": self.source,
                "meta": {"status_code": status_code},
            }
        if not rates:
            raise ApiRequestError("ExchangeRate-API: в ответе нет корректных курсов")
        return rates


def _valid_rate(value: Any) -> bool:
    return (
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        and isfinite(value)
        and value > 0
    )


def _http_error_message(status_code: int) -> str:
    if status_code == 401:
        return "HTTP 401: проверьте API-ключ и его доступ"
    if status_code == 403:
        return "HTTP 403: у API-ключа нет нужных прав"
    if status_code == 429:
        return "HTTP 429: превышен лимит запросов; подождите и повторите"
    if 500 <= status_code < 600:
        return f"HTTP {status_code}: источник временно недоступен; попробуйте позже"
    return f"HTTP {status_code}"


def _parse_exchange_timestamp(value: Any) -> str:
    if isinstance(value, str):
        try:
            return parsedate_to_datetime(value).astimezone(timezone.utc).isoformat()
        except (TypeError, ValueError, OverflowError):
            pass
    return datetime.now(timezone.utc).isoformat()
