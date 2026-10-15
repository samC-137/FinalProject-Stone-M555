import unittest
from argparse import Namespace
from contextlib import redirect_stdout
from io import StringIO
from unittest.mock import patch

from valutatrade_hub.cli.interface import _run_command


class TestRateCommandAccess(unittest.TestCase):
    def test_get_rate_does_not_require_login(self) -> None:
        arguments = Namespace(command="get-rate", from_code="EUR", to_code="USD")
        rate = {
            "from_currency": "EUR",
            "to_currency": "USD",
            "rate": 1.1,
            "updated_at": "2026-10-15T00:00:00+00:00",
        }
        output = StringIO()

        with patch("valutatrade_hub.cli.interface.get_rate", return_value=rate):
            with redirect_stdout(output):
                _run_command(arguments, None)

        self.assertIn("Курс EUR→USD: 1.10000000", output.getvalue())
        self.assertNotIn("Сначала выполните login", output.getvalue())
