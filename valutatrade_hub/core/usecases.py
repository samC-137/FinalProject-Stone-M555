from valutatrade_hub.core.exceptions import (
    InvalidPasswordError,
    UsernameAlreadyExistsError,
    UserNotFoundError,
)
from valutatrade_hub.core.models import User
from valutatrade_hub.infra.database import DatabaseManager


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

    updated_users = [*users, user.to_dict()]
    updated_portfolios = [*portfolios, {"user_id": user.user_id, "wallets": {}}]
    try:
        manager.save_users(updated_users)
        manager.save_portfolios(updated_portfolios)
    except Exception:
        manager.save_users(users)
        manager.save_portfolios(portfolios)
        raise

    return user


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
