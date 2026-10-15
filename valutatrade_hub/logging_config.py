import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path


def configure_logging(
    log_dir: Path | None = None,
    level: int = logging.INFO,
) -> None:
    """Настроить отдельные файлы для действий и работы парсера."""
    directory = log_dir or Path(__file__).resolve().parents[1] / "logs"
    directory.mkdir(parents=True, exist_ok=True)
    formatter = logging.Formatter("%(levelname)s %(message)s")

    _add_file_handler(
        logging.getLogger("valutatrade.actions"),
        directory / "actions.log",
        formatter,
        level,
    )
    parser_logger = logging.getLogger("valutatrade_hub.parser_service")
    parser_logger.setLevel(level)
    parser_logger.propagate = False
    _add_file_handler(
        parser_logger,
        directory / "parser.log",
        formatter,
        level,
    )


def _add_file_handler(
    logger: logging.Logger,
    path: Path,
    formatter: logging.Formatter,
    level: int,
) -> None:
    logger.setLevel(level)
    logger.propagate = False
    has_handler = any(
        getattr(handler, "_valutatrade_handler", False) for handler in logger.handlers
    )
    if has_handler:
        return

    handler = RotatingFileHandler(
        path,
        maxBytes=1_000_000,
        backupCount=3,
        encoding="utf-8",
    )
    handler._valutatrade_handler = True
    handler.setFormatter(formatter)
    handler.setLevel(level)
    logger.addHandler(handler)
