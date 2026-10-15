import unittest
from unittest.mock import patch

from valutatrade_hub.core.exceptions import ApiRequestError
from valutatrade_hub.parser_service.api_clients import BaseApiClient


class TestApiClientErrors(unittest.TestCase):
    def setUp(self) -> None:
        self.client = _TestApiClient()

    def test_explains_unauthorized_response(self) -> None:
        self._assert_error_message(
            401,
            "проверьте API-ключ",
        )

    def test_explains_rate_limit_response(self) -> None:
        self._assert_error_message(
            429,
            "превышен лимит запросов",
        )

    def test_explains_temporary_server_error(self) -> None:
        self._assert_error_message(
            503,
            "источник временно недоступен",
        )

    def test_keeps_status_for_other_http_errors(self) -> None:
        self._assert_error_message(404, "HTTP 404")

    def _assert_error_message(self, status_code: int, expected: str) -> None:
        response = _FakeResponse(status_code)
        with patch(
            "valutatrade_hub.parser_service.api_clients.requests.get",
            return_value=response,
        ):
            with self.assertRaises(ApiRequestError) as context:
                self.client._get_json("https://example.test/rates")

        self.assertIn(expected, str(context.exception))


class _TestApiClient(BaseApiClient):
    source = "Test API"

    def fetch_rates(self) -> dict[str, dict[str, object]]:
        return {}


class _FakeResponse:
    def __init__(self, status_code: int) -> None:
        self.status_code = status_code


if __name__ == "__main__":
    unittest.main()
