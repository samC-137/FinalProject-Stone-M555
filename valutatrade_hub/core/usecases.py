from datetime import datetime, timedelta, timezone
from math import isfinite
from typing import Any

from valutatrade_hub.core.currencies import get_currency
from valutatrade_hub.core.exceptions import (
    ApiRequestError,
    InvalidPasswordError,
    UsernameAlreadyExistsError,
    UserNotFoundError,
    WalletNotFoundError,
)
from valutatrade_hub.core.models import Portfolio, User, Wallet
from valutatrade_hub.core.utils import convert_amount
from valutatrade_hub.decorators import log_action
from valutatrade_hub.infra.database import DatabaseManager
from valutatrade_hub.infra.settings import SettingsLoader


@log_action("REGISTER")
def register_user(
    username: str,
    password: str,
    database: DatabaseManager | None = None,
) -> User:
    """Зарегистрировать пользователя и создать ему пустой портфель."""
    manager = database or DatabaseManager()
    clean_username = username.strip() if isinstance(username, str) else username
    users = manager.load_users()
    if any(user.get("username") == clean_username for user in users):
        raise UsernameAlreadyExistsError(clean_username)

    next_id = max((user.get("user_id", 0) for user in users), default=0) + 1
    user = User.create(next_id, clean_username, password)
    portfolios = manager.load_portfolios()

    starting_balance = SettingsLoader().get("starting_balance_usd", 10000)
    usd_wallet = Wallet("USD", float(starting_balance))
    updated_users = [*users, user.to_dict()]
    updated_portfolios = [
        *portfolios,
        {
            "user_id": user.user_id,
            "wallets": {"USD": {"balance": usd_wallet.balance}},
        },
    ]
    try:
        manager.save_users(updated_users)
        manager.save_portfolios(updated_portfolios)
    except Exception:
        manager.save_users(users)
        manager.save_portfolios(portfolios)
        raise

    return user


@log_action("LOGIN")
def login_user(
    username: str,
    password: str,
    database: DatabaseManager | None = None,
) -> User:
    """Проверить данные входа и вернуть найденного пользователя."""
    manager = database or DatabaseManager()
    clean_username = username.strip() if isinstance(username, str) else username
    user_data = next(
        (
            item
            for item in manager.load_users()
            if item.get("username") == clean_username
        ),
        None,
    )
    if user_data is None:
        raise UserNotFoundError(clean_username)

    user = User.from_dict(user_data)
    if not user.verify_password(password):
        raise InvalidPasswordError()
    return user


def get_rate(
    from_code: str,
    to_code: str,
    database: DatabaseManager | None = None,
    settings: SettingsLoader | None = None,
) -> dict[str, Any]:
    """Получить свежий курс, при необходимости обновив локальный кэш."""
    source_code = get_currency(from_code).code
    target_code = get_currency(to_code).code
    manager = database or DatabaseManager()
    config = settings or SettingsLoader()
    try:
        return _get_cached_rate(source_code, target_code, manager, config)
    except ApiRequestError as cache_error:
        from valutatrade_hub.parser_service.storage import RatesStorage
        from valutatrade_hub.parser_service.updater import RatesUpdater

        update_result = RatesUpdater(storage=RatesStorage(manager)).run_update()
        try:
            return _get_cached_rate(source_code, target_code, manager, config)
        except ApiRequestError as refreshed_error:
            update_errors = update_result.get("errors", [])
            reason = refreshed_error.reason
            if update_errors:
                reason = f"{reason}; обновление: {'; '.join(update_errors)}"
            raise ApiRequestError(
                f"{reason}. Выполните 'update-rates' и попробуйте снова"
            ) from cache_error


def _get_cached_rate(
    source_code: str,
    target_code: str,
    manager: DatabaseManager,
    config: SettingsLoader,
) -> dict[str, Any]:
    """Найти курс в кэше и проверить срок его актуальности."""
    if source_code == target_code:
        now = datetime.now(timezone.utc).isoformat()
        return {
            "from_currency": source_code,
            "to_currency": target_code,
            "rate": 1.0,
            "updated_at": now,
            "source": "local",
        }

    cache = manager.load_rates()
    pairs = cache.get("pairs", {})
    if not isinstance(pairs, dict):
        raise ApiRequestError("кэш курсов имеет неверный формат")

    direct = _read_cached_pair(source_code, target_code, pairs)
    if direct is not None:
        rate, updated_at, source = direct
    else:
        reverse = _read_cached_pair(target_code, source_code, pairs)
        if reverse is not None:
            reverse_rate, updated_at, source = reverse
            rate = 1 / reverse_rate
        elif source_code != "USD" and target_code != "USD":
            first = _get_cached_rate(source_code, "USD", manager, config)
            second = _get_cached_rate("USD", target_code, manager, config)
            rate = first["rate"] * second["rate"]
            first_time = datetime.fromisoformat(first["updated_at"])
            second_time = datetime.fromisoformat(second["updated_at"])
            updated_at = min(first_time, second_time).isoformat()
            source = f"{first['source']} + {second['source']}"
        else:
            raise ApiRequestError(f"курс {source_code}→{target_code} недоступен")

    timestamp = _check_rate_freshness(
        source_code,
        target_code,
        updated_at,
        source,
        config,
    )
    return {
        "from_currency": source_code,
        "to_currency": target_code,
        "rate": rate,
        "updated_at": timestamp.isoformat(),
        "source": source,
    }


def show_portfolio(
    user: User,
    base_currency: str = "USD",
    database: DatabaseManager | None = None,
) -> tuple[Portfolio, float]:
    """Загрузить портфель и посчитать его стоимость в выбранной валюте."""
    manager = database or DatabaseManager()
    portfolio = _load_portfolio(user, manager)
    base_code = get_currency(base_currency).code
    rates: dict[str, float] = {}
    for code in portfolio.wallets:
        rates[f"{code}_{base_code}"] = get_rate(code, base_code, manager)["rate"]
    return portfolio, portfolio.get_total_value(base_code, rates)


@log_action("BUY", verbose=True)
def buy(
    user: User,
    currency_code: str,
    amount: float,
    database: DatabaseManager | None = None,
) -> dict[str, Any]:
    """Добавить купленное количество валюты в портфель."""
    Wallet._validate_amount(amount)
    code = get_currency(currency_code).code
    if code == "USD":
        raise ValueError("USD используется для расчётов и не покупается")
    manager = database or DatabaseManager()
    rate = get_rate(code, "USD", manager)
    portfolio = _load_portfolio(user, manager)
    usd_wallet = portfolio.get_wallet("USD")
    if usd_wallet is None:
        usd_wallet = portfolio.add_currency("USD")
    usd_wallet.withdraw(convert_amount(amount, rate["rate"]))
    wallet = portfolio.get_wallet(code)
    if wallet is None:
        wallet = portfolio.add_currency(code)
    old_balance = wallet.balance
    wallet.deposit(amount)
    _save_portfolio(portfolio, manager)
    return {
        "currency_code": code,
        "amount": amount,
        "old_balance": old_balance,
        "new_balance": wallet.balance,
        "rate": rate["rate"],
        "value_usd": amount * rate["rate"],
    }


@log_action("SELL", verbose=True)
def sell(
    user: User,
    currency_code: str,
    amount: float,
    database: DatabaseManager | None = None,
) -> dict[str, Any]:
    """Уменьшить баланс кошелька на проданное количество валюты."""
    Wallet._validate_amount(amount)
    code = get_currency(currency_code).code
    if code == "USD":
        raise ValueError("USD используется для расчётов и не продаётся")
    manager = database or DatabaseManager()
    portfolio = _load_portfolio(user, manager)
    wallet = portfolio.get_wallet(code)
    if wallet is None:
        raise WalletNotFoundError(code)
    rate = get_rate(code, "USD", manager)
    old_balance = wallet.balance
    wallet.withdraw(amount)
    usd_wallet = portfolio.get_wallet("USD")
    if usd_wallet is None:
        usd_wallet = portfolio.add_currency("USD")
    usd_wallet.deposit(convert_amount(amount, rate["rate"]))
    _save_portfolio(portfolio, manager)
    return {
        "currency_code": code,
        "amount": amount,
        "old_balance": old_balance,
        "new_balance": wallet.balance,
        "rate": rate["rate"],
        "value_usd": amount * rate["rate"],
    }


def _load_portfolio(user: User, database: DatabaseManager) -> Portfolio:
    portfolios = database.load_portfolios()
    portfolio_data = next(
        (item for item in portfolios if item.get("user_id") == user.user_id),
        None,
    )
    if portfolio_data is None:
        raise ValueError(f"Портфель пользователя '{user.username}' не найден")
    return Portfolio.from_dict(portfolio_data, user)


def _save_portfolio(portfolio: Portfolio, database: DatabaseManager) -> None:
    portfolios = database.load_portfolios()
    for index, item in enumerate(portfolios):
        if item.get("user_id") == portfolio.user_id:
            portfolios[index] = portfolio.to_dict()
            database.save_portfolios(portfolios)
            return
    raise ValueError(f"Портфель пользователя '{portfolio.user.username}' не найден")


def _read_cached_pair(
    from_code: str,
    to_code: str,
    pairs: dict[str, Any],
) -> tuple[float, str, str] | None:
    value = pairs.get(f"{from_code}_{to_code}")
    if value is None:
        return None
    if not isinstance(value, dict):
        raise ApiRequestError(
            f"данные курса {from_code}→{to_code} имеют неверный формат"
        )
    rate = value.get("rate")
    updated_at = value.get("updated_at")
    if (
        isinstance(rate, bool)
        or not isinstance(rate, (int, float))
        or not isfinite(rate)
        or rate <= 0
        or not isinstance(updated_at, str)
    ):
        raise ApiRequestError(f"данные курса {from_code}→{to_code} неполные")
    return float(rate), updated_at, str(value.get("source", "cache"))


def _check_rate_freshness(
    from_code: str,
    to_code: str,
    updated_at: str,
    source: str,
    settings: SettingsLoader,
) -> datetime:
    try:
        timestamp = datetime.fromisoformat(updated_at.replace("Z", "+00:00"))
    except ValueError as error:
        raise ApiRequestError(
            f"время курса {from_code}→{to_code} некорректно"
        ) from error
    if timestamp.tzinfo is None:
        timestamp = timestamp.replace(tzinfo=timezone.utc)
    is_fiat_rate = "ExchangeRate-API" in source
    ttl_key = "fiat_rates_ttl_seconds" if is_fiat_rate else "rates_ttl_seconds"
    default_ttl = 86400 if is_fiat_rate else 300
    ttl = int(settings.get(ttl_key, default_ttl))
    if datetime.now(timezone.utc) - timestamp > timedelta(seconds=ttl):
        raise ApiRequestError(
            f"курс {from_code}→{to_code} устарел; обновите курсы "
            "командой 'update-rates'"
        )
    return timestamp
