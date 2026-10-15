class CurrencyNotFoundError(Exception):
    """Возникает, если код валюты не поддерживается."""

    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(f"Неизвестная валюта '{code}'")
