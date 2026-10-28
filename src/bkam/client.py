import os
from datetime import date

import httpx

from bkam.exceptions import (
    APIError,
    AuthenticationError,
    BKAMConnectionError,
    ConfigurationError,
    RateLimitError,
)
from bkam.models import BanknoteRate, TransferRate

BASE_URL = "https://api.centralbankofmorocco.ma/cours/Version1/api"
API_KEY_ENV_VAR = "BKAM_API_KEY"


class BKAMClient:
    """Synchronous client for the Bank Al-Maghrib exchange-rate API."""

    def __init__(
        self,
        api_key: str | None = None,
        *,
        base_url: str = BASE_URL,
        timeout: float = 10.0,
    ):
        key = api_key or os.environ.get(API_KEY_ENV_VAR)
        if not key:
            raise ConfigurationError(
                f"No API key given. Pass api_key=... "
                f"or set the {API_KEY_ENV_VAR} environment variable."
            )
        self._http = httpx.Client(
            base_url=base_url,
            headers={"Ocp-Apim-Subscription-Key": key},
            timeout=timeout,
        )

    def get_banknote_rates(
        self,
        currency: str | None = None,
        on: date | None = None,
    ) -> list[BanknoteRate]:
        items = self._get_rates("/CoursBBE", currency, on)
        return [BanknoteRate.model_validate(item) for item in items]

    def get_transfer_rates(
        self,
        currency: str | None = None,
        on: date | None = None,
    ) -> list[TransferRate]:
        items = self._get_rates("/CoursVirement", currency, on)
        return [TransferRate.model_validate(item) for item in items]

    def _get_rates(
        self,
        path: str,
        currency: str | None,
        on: date | None,
    ) -> list[dict]:
        params: dict[str, str] = {}
        if currency is not None:
            params["libDevise"] = currency.upper()
        if on is not None:
            params["date"] = on.isoformat()

        try:
            response = self._http.get(path, params=params)
        except httpx.TransportError as exc:
            raise BKAMConnectionError(f"Could not reach the BKAM API: {exc}") from exc

        if response.is_error:
            raise _error_from_response(response)
        return response.json()

    def close(self) -> None:
        self._http.close()

    def __enter__(self) -> "BKAMClient":
        return self

    def __exit__(self, *exc_info) -> None:
        self.close()


def _error_from_response(response: httpx.Response) -> APIError:
    message = _error_message(response)
    status = response.status_code
    if status == 401:
        return AuthenticationError(message, status)
    if status == 429:
        return RateLimitError(message, status, retry_after=_retry_after(response))
    return APIError(message, status)


def _error_message(response: httpx.Response) -> str:
    try:
        body = response.json()
    except ValueError:
        body = None
    if isinstance(body, dict) and isinstance(body.get("message"), str):
        return body["message"]
    return f"HTTP {response.status_code}: {response.reason_phrase}"


def _retry_after(response: httpx.Response) -> float | None:
    value = response.headers.get("Retry-After")
    if value is None:
        return None
    try:
        return float(value)
    except ValueError:
        return None