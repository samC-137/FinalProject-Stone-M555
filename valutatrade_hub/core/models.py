import hashlib
import hmac
import secrets
from datetime import datetime
from math import isfinite
from typing import Any

from valutatrade_hub.core.currencies import get_currency
from valutatrade_hub.core.exceptions import ApiRequestError, InsufficientFundsError


class User:
    """Пользователь приложения."""

    def __init__(
        self,
        user_id: int,
        username: str,
        hashed_password: str,
        salt: str,
        registration_date: datetime,
    ) -> None:
        if isinstance(user_id, bool) or not isinstance(user_id, int) or user_id < 1:
            raise ValueError("ID пользователя должен быть положительным числом")
        if not isinstance(hashed_password, str):
            raise ValueError("Хеш пароля должен быть строкой")
        if not isinstance(salt, str):
            raise ValueError("Соль должна быть строкой")
        if not isinstance(registration_date, datetime):
            raise ValueError("Дата регистрации должна иметь тип datetime")

        self._user_id = user_id
        self._username = username
        self._hashed_password = hashed_password
        self._salt = salt
        self._registration_date = registration_date
        self._validate_username(username)

    @staticmethod
    def _validate_username(username: str) -> None:
        if not isinstance(username, str) or not username.strip():
            raise ValueError("Имя пользователя не должно быть пустым")

    @staticmethod
    def _hash_password(password: str, salt: str) -> str:
        return hashlib.sha256(f"{password}{salt}".encode("utf-8")).hexdigest()

    @classmethod
    def create(cls, user_id: int, username: str, password: str) -> "User":
        """Создать пользователя и сразу сохранить пароль в виде хеша."""
        cls._validate_username(username)
        cls._validate_password(password)
        salt = secrets.token_hex(16)
        hashed_password = cls._hash_password(password, salt)
        return cls(user_id, username, hashed_password, salt, datetime.now())

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "User":
        """Восстановить пользователя из JSON-совместимых данных."""
        try:
            registration_date = datetime.fromisoformat(data["registration_date"])
            return cls(
                user_id=data["user_id"],
                username=data["username"],
                hashed_password=data["hashed_password"],
                salt=data["salt"],
                registration_date=registration_date,
            )
        except (KeyError, TypeError, ValueError) as error:
            raise ValueError("Данные пользователя имеют неверный формат") from error

    @staticmethod
    def _validate_password(password: str) -> None:
        if not isinstance(password, str) or len(password) < 4:
            raise ValueError("Пароль должен быть не короче 4 символов")

    @property
    def user_id(self) -> int:
        """Вернуть ID пользователя."""
        return self._user_id

    @property
    def username(self) -> str:
        """Вернуть имя пользователя."""
        return self._username

    @username.setter
    def username(self, value: str) -> None:
        self._validate_username(value)
        self._username = value

    @property
    def hashed_password(self) -> str:
        """Вернуть хеш пароля для сохранения пользователя."""
        return self._hashed_password

    @property
    def salt(self) -> str:
        """Вернуть соль для сохранения пользователя."""
        return self._salt

    @property
    def registration_date(self) -> datetime:
        """Вернуть дату регистрации."""
        return self._registration_date

    def get_user_info(self) -> dict[str, int | str]:
        """Вернуть общую информацию без хеша и соли."""
        return {
            "user_id": self._user_id,
            "username": self._username,
            "registration_date": self._registration_date.isoformat(),
        }

    def change_password(self, new_password: str) -> None:
        """Заменить пароль, создав новую соль и хеш."""
        self._validate_password(new_password)
        self._salt = secrets.token_hex(16)
        self._hashed_password = self._hash_password(new_password, self._salt)

    def verify_password(self, password: str) -> bool:
        """Проверить пароль, не раскрывая сохранённые данные."""
        if not isinstance(password, str):
            return False
        candidate_hash = self._hash_password(password, self._salt)
        return hmac.compare_digest(self._hashed_password, candidate_hash)

    def to_dict(self) -> dict[str, int | str]:
        """Подготовить данные пользователя для JSON-хранилища."""
        return {
            "user_id": self._user_id,
            "username": self._username,
            "hashed_password": self._hashed_password,
            "salt": self._salt,
            "registration_date": self._registration_date.isoformat(),
        }


class Wallet:
    """Кошелёк с балансом одной валюты."""

    def __init__(self, currency_code: str, balance: float = 0.0) -> None:
        self._currency_code = get_currency(currency_code).code
        self._balance = 0.0
        self.balance = balance

    @property
    def currency_code(self) -> str:
        """Вернуть код валюты кошелька."""
        return self._currency_code

    @property
    def balance(self) -> float:
        """Вернуть текущий баланс."""
        return self._balance

    @balance.setter
    def balance(self, value: float) -> None:
        if (
            isinstance(value, bool)
            or not isinstance(value, (int, float))
            or not isfinite(value)
            or value < 0
        ):
            raise ValueError("Баланс должен быть неотрицательным числом")
        self._balance = float(value)

    @staticmethod
    def _validate_amount(amount: float) -> None:
        if (
            isinstance(amount, bool)
            or not isinstance(amount, (int, float))
            or not isfinite(amount)
            or amount <= 0
        ):
            raise ValueError("Сумма должна быть положительным числом")

    def deposit(self, amount: float) -> None:
        """Добавить средства на кошелёк."""
        self._validate_amount(amount)
        self.balance = self._balance + amount

    def withdraw(self, amount: float) -> None:
        """Снять средства, если баланса хватает."""
        self._validate_amount(amount)
        if amount > self._balance:
            raise InsufficientFundsError(self._balance, amount, self._currency_code)
        self.balance = self._balance - amount

    def get_balance_info(self) -> str:
        """Вернуть баланс в удобном для показа виде."""
        return f"{self._currency_code}: {self._balance:.4f}"

    def to_dict(self) -> dict[str, str | float]:
        """Подготовить кошелёк для JSON-хранилища."""
        return {"currency_code": self._currency_code, "balance": self._balance}


class Portfolio:
    """Кошельки одного пользователя."""

    def __init__(
        self,
        user: User,
        wallets: dict[str, Wallet] | None = None,
    ) -> None:
        if not isinstance(user, User):
            raise ValueError("Портфель должен быть связан с пользователем")
        self._user = user
        self._wallets: dict[str, Wallet] = {}
        for code, wallet in (wallets or {}).items():
            if not isinstance(wallet, Wallet) or wallet.currency_code != code:
                raise ValueError("Ключ портфеля должен совпадать с валютой кошелька")
            self._wallets[code] = wallet

    @property
    def user(self) -> User:
        """Вернуть владельца портфеля."""
        return self._user

    @property
    def user_id(self) -> int:
        """Вернуть ID владельца портфеля."""
        return self._user.user_id

    @property
    def wallets(self) -> dict[str, Wallet]:
        """Вернуть копию словаря кошельков."""
        return self._wallets.copy()

    def add_currency(self, currency_code: str) -> Wallet:
        """Добавить пустой кошелёк, если такой валюты ещё нет."""
        code = get_currency(currency_code).code
        if code in self._wallets:
            raise ValueError(f"Кошелёк '{code}' уже есть в портфеле")
        wallet = Wallet(code)
        self._wallets[code] = wallet
        return wallet

    def get_wallet(self, currency_code: str) -> Wallet | None:
        """Вернуть кошелёк или None, если он ещё не добавлен."""
        code = get_currency(currency_code).code
        return self._wallets.get(code)

    def get_total_value(
        self,
        base_currency: str = "USD",
        exchange_rates: dict[str, Any] | None = None,
    ) -> float:
        """Посчитать стоимость портфеля по переданным курсам."""
        base_code = get_currency(base_currency).code
        if exchange_rates is None:
            from valutatrade_hub.infra.database import DatabaseManager

            exchange_rates = DatabaseManager().load_rates()
        pairs = exchange_rates
        if "pairs" in pairs and isinstance(pairs["pairs"], dict):
            pairs = pairs["pairs"]

        total = 0.0
        for code, wallet in self._wallets.items():
            rate = self._get_conversion_rate(code, base_code, pairs)
            total += wallet.balance * rate
        return total

    @classmethod
    def from_dict(cls, data: dict[str, Any], user: User) -> "Portfolio":
        """Восстановить портфель из JSON-совместимых данных."""
        wallets_data = data.get("wallets", {})
        if not isinstance(wallets_data, dict):
            raise ValueError("Список кошельков в портфеле имеет неверный формат")
        wallets = {
            code: Wallet(code, wallet_data["balance"])
            for code, wallet_data in wallets_data.items()
        }
        return cls(user, wallets)

    def to_dict(self) -> dict[str, Any]:
        """Подготовить портфель для JSON-хранилища."""
        return {
            "user_id": self.user_id,
            "wallets": {
                code: {"balance": wallet.balance}
                for code, wallet in self._wallets.items()
            },
        }

    @staticmethod
    def _get_conversion_rate(
        from_code: str,
        to_code: str,
        pairs: dict[str, Any],
    ) -> float:
        if from_code == to_code:
            return 1.0

        direct_rate = Portfolio._read_pair_rate(from_code, to_code, pairs)
        if direct_rate is not None:
            return direct_rate
        reverse_rate = Portfolio._read_pair_rate(to_code, from_code, pairs)
        if reverse_rate is not None:
            return 1.0 / reverse_rate

        if from_code != "USD" and to_code != "USD":
            to_usd = Portfolio._get_conversion_rate(from_code, "USD", pairs)
            usd_to_base = Portfolio._get_conversion_rate("USD", to_code, pairs)
            return to_usd * usd_to_base

        raise ApiRequestError(f"не найден курс {from_code}→{to_code}")

    @staticmethod
    def _read_pair_rate(
        from_code: str,
        to_code: str,
        pairs: dict[str, Any],
    ) -> float | None:
        value = pairs.get(f"{from_code}_{to_code}")
        if isinstance(value, dict):
            value = value.get("rate")
        if value is None:
            return None
        if (
            isinstance(value, bool)
            or not isinstance(value, (int, float))
            or not isfinite(value)
            or value <= 0
        ):
            raise ApiRequestError(f"некорректный курс {from_code}→{to_code}")
        return float(value)
