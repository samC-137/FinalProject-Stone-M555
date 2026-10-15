class CurrencyNotFoundError(Exception):
    """Возникает, если код валюты не поддерживается."""

    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(f"Неизвестная валюта '{code}'")


class InsufficientFundsError(Exception):
    """Возникает, если в кошельке недостаточно средств для снятия."""

    def __init__(self, available: float, required: float, code: str) -> None:
        self.available = available
        self.required = required
        self.code = code
        super().__init__(
            f"Недостаточно средств: доступно {available:.4f} {code}, "
            f"требуется {required:.4f} {code}"
        )


class ApiRequestError(Exception):
    """Возникает, если не удалось получить нужный курс валют."""

    def __init__(self, reason: str) -> None:
        self.reason = reason
        super().__init__(f"Ошибка при обращении к внешнему API: {reason}")


class UsernameAlreadyExistsError(Exception):
    """Возникает, если имя пользователя уже занято."""

    def __init__(self, username: str) -> None:
        self.username = username
        super().__init__(f"Имя пользователя '{username}' уже занято")


class UserNotFoundError(Exception):
    """Возникает, если пользователь не зарегистрирован."""

    def __init__(self, username: str) -> None:
        self.username = username
        super().__init__(f"Пользователь '{username}' не найден")


class InvalidPasswordError(Exception):
    """Возникает, если пароль не совпадает."""

    def __init__(self) -> None:
        super().__init__("Неверный пароль")
