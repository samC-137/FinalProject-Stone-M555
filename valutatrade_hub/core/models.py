import hashlib
import hmac
import secrets
from datetime import datetime


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
