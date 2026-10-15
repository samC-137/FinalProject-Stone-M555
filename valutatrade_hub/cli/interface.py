import argparse
import shlex

from prettytable import PrettyTable

from valutatrade_hub.core.models import User
from valutatrade_hub.core.usecases import (
    buy,
    get_rate,
    login_user,
    register_user,
    sell,
    show_portfolio,
)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="valutatrade")
    commands = parser.add_subparsers(dest="command", required=True)

    register_parser = commands.add_parser("register", help="Создать пользователя")
    register_parser.add_argument("--username", required=True)
    register_parser.add_argument("--password", required=True)

    login_parser = commands.add_parser("login", help="Войти в систему")
    login_parser.add_argument("--username", required=True)
    login_parser.add_argument("--password", required=True)

    portfolio_parser = commands.add_parser(
        "show-portfolio",
        help="Показать портфель",
    )
    portfolio_parser.add_argument("--base", default="USD")

    for name, help_text in (
        ("buy", "Купить валюту"),
        ("sell", "Продать валюту"),
    ):
        trade_parser = commands.add_parser(name, help=help_text)
        trade_parser.add_argument("--currency", required=True)
        trade_parser.add_argument("--amount", required=True, type=float)

    rate_parser = commands.add_parser("get-rate", help="Показать курс валют")
    rate_parser.add_argument("--from", dest="from_code", required=True)
    rate_parser.add_argument("--to", dest="to_code", required=True)

    commands.add_parser("exit", help="Закрыть программу")
    return parser


def main() -> None:
    """Запустить интерактивный командный интерфейс."""
    parser = _build_parser()
    current_user: User | None = None
    print("ValutaTrade Hub. Введите 'help' для списка команд или 'exit' для выхода.")

    while True:
        try:
            command_line = input("> ")
        except (EOFError, KeyboardInterrupt):
            print("\nДо свидания!")
            return

        if command_line.strip() == "help":
            parser.print_help()
            continue
        if not command_line.strip():
            continue

        try:
            arguments = parser.parse_args(shlex.split(command_line))
            if arguments.command == "exit":
                print("До свидания!")
                return
            current_user = _run_command(arguments, current_user)
        except SystemExit:
            continue
        except Exception as error:
            print(str(error))


def _run_command(arguments: argparse.Namespace, user: User | None) -> User | None:
    if arguments.command == "register":
        registered_user = register_user(arguments.username, arguments.password)
        print(
            f"Пользователь '{registered_user.username}' зарегистрирован "
            f"(id={registered_user.user_id}). Войдите: login --username "
            f"{registered_user.username} --password ****"
        )
        return user

    if arguments.command == "login":
        current_user = login_user(arguments.username, arguments.password)
        print(f"Вы вошли как '{current_user.username}'")
        return current_user

    if user is None:
        print("Сначала выполните login")
        return None

    if arguments.command == "show-portfolio":
        portfolio, total = show_portfolio(user, arguments.base)
        print(f"Портфель пользователя '{user.username}' (база: {arguments.base}):")
        if not portfolio.wallets:
            print("Портфель пока пуст.")
            return user

        table = PrettyTable(["Валюта", "Баланс", f"Стоимость ({arguments.base})"])
        for code, wallet in portfolio.wallets.items():
            rate_info = get_rate(code, arguments.base)
            value = wallet.balance * rate_info["rate"]
            table.add_row([code, f"{wallet.balance:.4f}", f"{value:.2f}"])
        print(table)
        print(f"ИТОГО: {total:.2f} {arguments.base}")
        return user

    if arguments.command in {"buy", "sell"}:
        operation = buy if arguments.command == "buy" else sell
        result = operation(user, arguments.currency, arguments.amount)
        title = "Покупка" if arguments.command == "buy" else "Продажа"
        print(
            f"{title} выполнена: {result['amount']:.4f} "
            f"{result['currency_code']} по курсу {result['rate']:.6f} USD"
        )
        print(
            f"Баланс: {result['old_balance']:.4f} → "
            f"{result['new_balance']:.4f} {result['currency_code']}"
        )
        label = "Стоимость" if arguments.command == "buy" else "Выручка"
        print(f"Оценочная {label.lower()}: {result['value_usd']:.2f} USD")
        return user

    if arguments.command == "get-rate":
        rate_info = get_rate(arguments.from_code, arguments.to_code)
        rate = rate_info["rate"]
        reverse_rate = 1 / rate
        print(
            f"Курс {rate_info['from_currency']}→{rate_info['to_currency']}: "
            f"{rate:.8f} (обновлено: {rate_info['updated_at']})"
        )
        print(
            f"Обратный курс {rate_info['to_currency']}→"
            f"{rate_info['from_currency']}: {reverse_rate:.8f}"
        )
        return user

    return user
