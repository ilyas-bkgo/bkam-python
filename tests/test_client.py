from datetime import date
from decimal import Decimal

import httpx
import pytest
import respx

from bkam.client import BASE_URL, BKAMClient

EUR_PAYLOAD = {
    "achatClientele": 10.098,
    "date": "2026-10-16T08:30:00",
    "libDevise": "EUR",
    "uniteDevise": 1,
    "venteClientele": 11.7356,
}

JPY_TRANSFER_PAYLOAD = {
    "date": "2026-10-16T12:30:00",
    "libDevise": "JPY",
    "moyen": 6.1508,
    "uniteDevise": 100,
}

@respx.mock
def test_get_banknote_rates_returns_models():
    respx.get(f"{BASE_URL}/CoursBBE").mock(
        return_value=httpx.Response(200, json=[EUR_PAYLOAD])
    )

    with BKAMClient(api_key="test-key") as client:
        rates = client.get_banknote_rates()

    assert len(rates) == 1
    assert rates[0].currency == "EUR"
    assert rates[0].buy == Decimal("10.098")


@respx.mock
def test_sends_key_and_query_parameters():
    route = respx.get(f"{BASE_URL}/CoursBBE").mock(
        return_value=httpx.Response(200, json=[EUR_PAYLOAD])
    )

    with BKAMClient(api_key="test-key") as client:
        client.get_banknote_rates(currency="eur", on=date(2026, 10, 16))

    request = route.calls.last.request
    assert request.headers["Ocp-Apim-Subscription-Key"] == "test-key"
    assert request.url.params["libDevise"] == "EUR"
    assert request.url.params["date"] == "2026-10-16"


@respx.mock
def test_empty_response_gives_empty_list():
    # BKAM answers 200 with [] on weekends and holidays
    respx.get(f"{BASE_URL}/CoursBBE").mock(
        return_value=httpx.Response(200, json=[])
    )

    with BKAMClient(api_key="test-key") as client:
        assert client.get_banknote_rates(on=date(2026, 10, 18)) == []


def test_missing_api_key_raises(monkeypatch):
    monkeypatch.delenv("BKAM_API_KEY", raising=False)

    with pytest.raises(ValueError):
        BKAMClient()


@respx.mock
def test_get_transfer_rates_returns_models():
    respx.get(f"{BASE_URL}/CoursVirement").mock(
        return_value=httpx.Response(200, json=[JPY_TRANSFER_PAYLOAD])
    )

    with BKAMClient(api_key="test-key") as client:
        rates = client.get_transfer_rates()

    assert len(rates) == 1
    assert rates[0].currency == "JPY"
    assert rates[0].average == Decimal("6.1508")
    assert rates[0].average_per_unit == Decimal("0.061508")


@respx.mock
def test_transfer_rates_send_key_and_query_parameters():
    route = respx.get(f"{BASE_URL}/CoursVirement").mock(
        return_value=httpx.Response(200, json=[JPY_TRANSFER_PAYLOAD])
    )

    with BKAMClient(api_key="test-key") as client:
        client.get_transfer_rates(currency="jpy", on=date(2026, 10, 16))

    request = route.calls.last.request
    assert request.headers["Ocp-Apim-Subscription-Key"] == "test-key"
    assert request.url.params["libDevise"] == "JPY"
    assert request.url.params["date"] == "2026-10-16"