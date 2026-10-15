from abc import ABC, abstractmethod
from dataclasses import dataclass
from math import isfinite

from valutatrade_hub.core.exceptions import CurrencyNotFoundError
from valutatrade_hub.core.utils import normalize_currency_code


@dataclass(frozen=True)
class Currency(ABC):
    """Общие данные валюты."""

    code: str
    name: str

    def __post_init__(self) -> None:
        try:
            valid_code = normalize_currency_code(self.code) == self.code
        except (AttributeError, ValueError):
            valid_code = False
        if not valid_code:
            raise ValueError("Код валюты должен содержать 2–5 заглавных букв")
        if not isinstance(self.name, str) or not self.name.strip():
            raise ValueError("Название валюты не должно быть пустым")

    @abstractmethod
    def get_display_info(self) -> str:
        """Вернуть краткое описание валюты."""


@dataclass(frozen=True)
class FiatCurrency(Currency):
    """Фиатная валюта с указанием страны или зоны эмиссии."""

    issuing_country: str

    def __post_init__(self) -> None:
        super().__post_init__()
        if (
            not isinstance(self.issuing_country, str)
            or not self.issuing_country.strip()
        ):
            raise ValueError("Страна или зона эмиссии не должна быть пустой")

    def get_display_info(self) -> str:
        """Вернуть описание фиатной валюты."""
        return f"[FIAT] {self.code} — {self.name} (Issuing: {self.issuing_country})"


@dataclass(frozen=True)
class CryptoCurrency(Currency):
    """Криптовалюта с алгоритмом и последней известной капитализацией."""

    algorithm: str
    market_cap: float

    def __post_init__(self) -> None:
        super().__post_init__()
        if not isinstance(self.algorithm, str) or not self.algorithm.strip():
            raise ValueError("Алгоритм не должен быть пустым")
        if (
            isinstance(self.market_cap, bool)
            or not isinstance(self.market_cap, (int, float))
            or not isfinite(self.market_cap)
            or self.market_cap < 0
        ):
            raise ValueError("Капитализация должна быть неотрицательным числом")

    def get_display_info(self) -> str:
        """Вернуть описание криптовалюты."""
        return (
            f"[CRYPTO] {self.code} — {self.name} "
            f"(Algo: {self.algorithm}, MCAP: {self.market_cap:.3g})"
        )


_CURRENCY_DATA: dict[str, tuple[type[Currency], tuple[object, ...]]] = {
    "USD": (FiatCurrency, ("US Dollar", "United States")),
    "EUR": (FiatCurrency, ("Euro", "Eurozone")),
    "GBP": (FiatCurrency, ("Pound Sterling", "United Kingdom")),
    "RUB": (FiatCurrency, ("Russian Ruble", "Russia")),
    "BTC": (CryptoCurrency, ("Bitcoin", "SHA-256", 0.0)),
    "ETH": (CryptoCurrency, ("Ethereum", "Ethash", 0.0)),
    "SOL": (CryptoCurrency, ("Solana", "Proof of History", 0.0)),
}


def get_currency(code: str) -> Currency:
    """Найти валюту по коду без учёта регистра."""
    try:
        normalized_code = normalize_currency_code(code)
    except ValueError:
        raise CurrencyNotFoundError(code) from None
    currency_data = _CURRENCY_DATA.get(normalized_code)
    if currency_data is None:
        raise CurrencyNotFoundError(code)

    currency_type, details = currency_data
    return currency_type(normalized_code, *details)
