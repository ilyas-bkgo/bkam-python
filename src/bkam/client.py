import os
from datetime import date

import httpx

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
            raise ValueError(
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

        response = self._http.get(path, params=params)
        response.raise_for_status()
        return response.json()

    def close(self) -> None:
        self._http.close()

    def __enter__(self) -> "BKAMClient":
        return self

    def __exit__(self, *exc_info) -> None:
        self.close()