import copy
import unittest
from datetime import datetime, timezone

from valutatrade_hub.core.exceptions import InsufficientFundsError
from valutatrade_hub.core.models import User
from valutatrade_hub.core.usecases import buy, register_user, sell


class TestTradeSettlement(unittest.TestCase):
    def setUp(self) -> None:
        now = datetime.now(timezone.utc).isoformat()
        self.database = _FakeDatabase(
            rates={
                "pairs": {
                    "BTC_USD": {
                        "rate": 50000.0,
                        "updated_at": now,
                        "source": "CoinGecko",
                    }
                }
            },
            portfolios=[
                {
                    "user_id": 1,
                    "wallets": {
                        "USD": {"balance": 1000.0},
                        "BTC": {"balance": 0.0},
                    },
                }
            ],
        )
        self.user = User.create(1, "trader", "pass")

    def test_buy_deducts_usd_and_adds_currency(self) -> None:
        buy(self.user, "BTC", 0.01, self.database)

        wallets = self.database.portfolios[0]["wallets"]
        self.assertEqual(wallets["USD"]["balance"], 500.0)
        self.assertEqual(wallets["BTC"]["balance"], 0.01)

    def test_buy_with_insufficient_usd_does_not_change_portfolio(self) -> None:
        before = copy.deepcopy(self.database.portfolios)

        with self.assertRaises(InsufficientFundsError):
            buy(self.user, "BTC", 0.1, self.database)

        self.assertEqual(self.database.portfolios, before)

    def test_sell_adds_usd_proceeds(self) -> None:
        self.database.portfolios[0]["wallets"]["BTC"]["balance"] = 0.02

        sell(self.user, "BTC", 0.01, self.database)

        wallets = self.database.portfolios[0]["wallets"]
        self.assertEqual(wallets["USD"]["balance"], 1500.0)
        self.assertEqual(wallets["BTC"]["balance"], 0.01)

    def test_registration_creates_usd_wallet_with_starting_funds(self) -> None:
        database = _FakeDatabase()

        user = register_user("new_trader", "pass", database)

        self.assertEqual(user.user_id, 1)
        self.assertEqual(database.portfolios[0]["wallets"]["USD"]["balance"], 10000.0)


class _FakeDatabase:
    def __init__(
        self,
        rates: dict[str, object] | None = None,
        portfolios: list[dict[str, object]] | None = None,
    ) -> None:
        self.rates = rates or {"pairs": {}}
        self.portfolios = portfolios or []
        self.users: list[dict[str, object]] = []

    def load_rates(self) -> dict[str, object]:
        return self.rates

    def load_portfolios(self) -> list[dict[str, object]]:
        return copy.deepcopy(self.portfolios)

    def save_portfolios(self, portfolios: list[dict[str, object]]) -> None:
        self.portfolios = copy.deepcopy(portfolios)

    def load_users(self) -> list[dict[str, object]]:
        return copy.deepcopy(self.users)

    def save_users(self, users: list[dict[str, object]]) -> None:
        self.users = copy.deepcopy(users)
