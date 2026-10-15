import logging
from datetime import datetime, timezone
from functools import wraps
from inspect import signature
from typing import Any, Callable, TypeVar

Function = TypeVar("Function", bound=Callable[..., Any])


def log_action(action: str, verbose: bool = False) -> Callable[[Function], Function]:
    """Записать результат доменной операции и пробросить её ошибки."""

    def decorate(function: Function) -> Function:
        function_signature = signature(function)
        logger = logging.getLogger("valutatrade.actions")

        @wraps(function)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            values = function_signature.bind(*args, **kwargs).arguments
            user = values.get("user")
            username = getattr(user, "username", values.get("username", "unknown"))
            user_id = getattr(user, "user_id", None)
            currency = values.get("currency_code", "-")
            amount = values.get("amount")
            details = [
                f"action={action}",
                f"user={username!r}",
            ]
            if user_id is not None:
                details.append(f"user_id={user_id}")
            details.extend(
                (f"currency={currency!r}", f"amount={_format_amount(amount)}")
            )

            try:
                result = function(*args, **kwargs)
            except Exception as error:
                details.extend(
                    (
                        "result=ERROR",
                        f"error_type={type(error).__name__}",
                        f"error_message={str(error)!r}",
                    )
                )
                _write_log(logger, details)
                raise

            if isinstance(result, dict):
                if "rate" in result:
                    details.append(f"rate={result['rate']:.8f}")
                if "value_usd" in result:
                    details.append("base='USD'")
                if verbose and "old_balance" in result:
                    details.append(
                        f"balance={result['old_balance']:.4f}"
                        f"→{result['new_balance']:.4f}"
                    )
            details.append("result=OK")
            _write_log(logger, details)
            return result

        return wrapper  # type: ignore[return-value]

    return decorate


def _format_amount(amount: Any) -> str:
    if isinstance(amount, (int, float)) and not isinstance(amount, bool):
        return f"{amount:.4f}"
    return "-" if amount is None else repr(amount)


def _write_log(logger: logging.Logger, details: list[str]) -> None:
    timestamp = datetime.now(timezone.utc).isoformat()
    logger.info("%s %s", timestamp, " ".join(details))
