import os
import time
from datetime import date
from typing import TypeVar

import httpx
from pydantic import BaseModel, ValidationError

from bkam.exceptions import (
    APIError,
    AuthenticationError,
    BKAMConnectionError,
    ConfigurationError,
    InvalidResponseError,
    RateLimitError,
)
from bkam.models import BanknoteRate, TransferRate

BASE_URL = "https://api.centralbankofmorocco.ma/cours/Version1/api"
API_KEY_ENV_VAR = "BKAM_API_KEY"

RETRY_STATUS_CODES = {429, 502, 503, 504}
MAX_RETRY_WAIT = 30.0  # seconds; a longer Retry-After is not waited for
T = TypeVar("T", bound=BaseModel)


def _sleep(seconds: float) -> None:
    time.sleep(seconds)


class BKAMClient:
    """Synchronous client for the Bank Al-Maghrib exchange-rate API."""

    def __init__(
        self,
        api_key: str | None = None,
        *,
        base_url: str = BASE_URL,
        timeout: float = 10.0,
        max_retries: int = 2,
        backoff_factor: float = 0.5,
    ):
        key = api_key or os.environ.get(API_KEY_ENV_VAR)
        if not key:
            raise ConfigurationError(
                f"No API key given. Pass api_key=... "
                f"or set the {API_KEY_ENV_VAR} environment variable."
            )
        if max_retries < 0:
            raise ConfigurationError("max_retries must be 0 or greater.")

        self._max_retries = max_retries
        self._backoff_factor = backoff_factor
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
        return _build_models(BanknoteRate, items)

    def get_transfer_rates(
        self,
        currency: str | None = None,
        on: date | None = None,
    ) -> list[TransferRate]:
        items = self._get_rates("/CoursVirement", currency, on)
        return _build_models(TransferRate, items)

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

        for attempt in range(self._max_retries + 1):
            is_last_attempt = attempt == self._max_retries

            try:
                response = self._http.get(path, params=params)
            except httpx.TransportError as exc:
                if is_last_attempt:
                    raise BKAMConnectionError(
                        f"Could not reach the BKAM API: {exc}"
                    ) from exc
                _sleep(self._backoff(attempt))
                continue

            if response.status_code in RETRY_STATUS_CODES and not is_last_attempt:
                delay = self._retry_delay(response, attempt)
                if delay is not None:
                    _sleep(delay)
                    continue

            if response.is_error:
                raise _error_from_response(response)
            return _decode_items(response)

        raise AssertionError("unreachable")  # the loop always returns or raises

    def _backoff(self, attempt: int) -> float:
        return self._backoff_factor * 2**attempt

    def _retry_delay(self, response: httpx.Response, attempt: int) -> float | None:
        retry_after = _retry_after(response)
        if retry_after is None:
            return self._backoff(attempt)
        if retry_after > MAX_RETRY_WAIT:
            return None  # too long to wait: let the caller handle the error
        return retry_after

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

    

def _decode_items(response: httpx.Response) -> list[dict]:
    try:
        body = response.json()
    except ValueError as exc:
        raise InvalidResponseError(
            "The BKAM API returned a body that is not valid JSON."
        ) from exc

    if not isinstance(body, list) or not all(isinstance(item, dict) for item in body):
        raise InvalidResponseError(
            f"Expected a JSON list of objects from the BKAM API, "
            f"got {type(body).__name__}."
        )
    return body


def _build_models(model: type[T], items: list[dict]) -> list[T]:
    try:
        return [model.model_validate(item) for item in items]
    except ValidationError as exc:
        raise InvalidResponseError(
            f"The BKAM API returned data in an unexpected format: {exc}"
        ) from exc