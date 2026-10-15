import os
from dataclasses import dataclass, field
from pathlib import Path


@dataclass(frozen=True)
class ParserConfig:
    """Настройки получения курсов валют."""

    EXCHANGERATE_API_KEY: str | None = field(
        default_factory=lambda: os.getenv("EXCHANGERATE_API_KEY")
    )
    COINGECKO_URL: str = "https://api.coingecko.com/api/v3/simple/price"
    EXCHANGERATE_API_URL: str = "https://v6.exchangerate-api.com/v6"
    BASE_CURRENCY: str = "USD"
    FIAT_CURRENCIES: tuple[str, ...] = ("EUR", "GBP", "RUB")
    CRYPTO_CURRENCIES: tuple[str, ...] = ("BTC", "ETH", "SOL")
    CRYPTO_ID_MAP: dict[str, str] = field(
        default_factory=lambda: {
            "BTC": "bitcoin",
            "ETH": "ethereum",
            "SOL": "solana",
        }
    )
    REQUEST_TIMEOUT: int = 10
    DATA_DIR: Path = field(
        default_factory=lambda: Path(__file__).resolve().parents[2] / "data"
    )

    @property
    def RATES_FILE_PATH(self) -> Path:
        return self.DATA_DIR / "rates.json"

    @property
    def HISTORY_FILE_PATH(self) -> Path:
        return self.DATA_DIR / "exchange_rates.json"


