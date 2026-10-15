import re


def normalize_currency_code(code: str) -> str:
    """Проверить код валюты и привести его к верхнему регистру."""
    normalized_code = code.strip().upper() if isinstance(code, str) else str(code)
    if not re.fullmatch(r"[A-Z]{2,5}", normalized_code):
        raise ValueError("Код валюты должен содержать 2–5 букв")
    return normalized_code


def convert_amount(amount: float, rate: float) -> float:
    """Пересчитать сумму по курсу обмена."""
    return amount * rate
