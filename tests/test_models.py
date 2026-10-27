from datetime import datetime
from decimal import Decimal

import pytest
from pydantic import ValidationError

from bkam.models import BanknoteRate
from bkam.models import BanknoteRate, TransferRate

# Real data copied from the BKAM API (2026-10-16)
JPY_PAYLOAD = {
    "achatClientele": 5.6872,
    "date": "2026-10-16T08:30:00",
    "libDevise": "JPY",
    "uniteDevise": 100,
    "venteClientele": 6.6094,
}

EUR_PAYLOAD = {
    "achatClientele": 10.098,
    "date": "2026-10-16T08:30:00",
    "libDevise": "EUR",
    "uniteDevise": 1,
    "venteClientele": 11.7356,
}

EUR_TRANSFER_PAYLOAD = {
    "date": "2026-10-16T12:30:00",
    "libDevise": "EUR",
    "moyen": 10.9272,
    "uniteDevise": 1,
}

JPY_TRANSFER_PAYLOAD = {
    "date": "2026-10-16T12:30:00",
    "libDevise": "JPY",
    "moyen": 6.1508,
    "uniteDevise": 100,
}

DZD_TRANSFER_PAYLOAD = {
    "date": "2026-10-16T12:30:00",
    "libDevise": "DZD",
    "moyen": 0.7226,
    "uniteDevise": 10,
}

def test_parses_api_payload():
    rate = BanknoteRate.model_validate(JPY_PAYLOAD)

    assert rate.currency == "JPY"
    assert rate.unit == 100
    assert rate.buy == Decimal("5.6872")
    assert rate.sell == Decimal("6.6094")
    assert rate.published_at == datetime(2026, 10, 16, 8, 30)


def test_per_unit_divides_by_unit():
    rate = BanknoteRate.model_validate(JPY_PAYLOAD)

    assert rate.buy_per_unit == Decimal("0.056872")
    assert rate.sell_per_unit == Decimal("0.066094")


def test_per_unit_is_unchanged_when_unit_is_one():
    rate = BanknoteRate.model_validate(EUR_PAYLOAD)

    assert rate.buy_per_unit == Decimal("10.098")


def test_rejects_invalid_number():
    bad_payload = {**EUR_PAYLOAD, "achatClientele": "abc"}

    with pytest.raises(ValidationError):
        BanknoteRate.model_validate(bad_payload)


def test_rate_is_read_only():
    rate = BanknoteRate.model_validate(EUR_PAYLOAD)

    with pytest.raises(ValidationError):
        rate.buy = Decimal("1")


## -------- Second class tests ---------    
def test_transfer_rate_parses_api_payload():
    rate = TransferRate.model_validate(EUR_TRANSFER_PAYLOAD)

    assert rate.currency == "EUR"
    assert rate.unit == 1
    assert rate.average == Decimal("10.9272")
    assert rate.published_at == datetime(2026, 10, 16, 12, 30)


def test_transfer_average_per_unit_with_unit_100():
    rate = TransferRate.model_validate(JPY_TRANSFER_PAYLOAD)

    assert rate.average_per_unit == Decimal("0.061508")


def test_transfer_average_per_unit_with_unit_10():
    rate = TransferRate.model_validate(DZD_TRANSFER_PAYLOAD)

    assert rate.average_per_unit == Decimal("0.07226")


def test_transfer_rate_rejects_invalid_number():
    bad_payload = {**EUR_TRANSFER_PAYLOAD, "moyen": "abc"}

    with pytest.raises(ValidationError):
        TransferRate.model_validate(bad_payload)


def test_transfer_rate_is_read_only():
    rate = TransferRate.model_validate(EUR_TRANSFER_PAYLOAD)

    with pytest.raises(ValidationError):
        rate.average = Decimal("1")