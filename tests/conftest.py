import pytest


@pytest.fixture(autouse=True)
def no_sleep(monkeypatch):
    """Replace the client's sleep with a recorder, so tests never wait."""
    sleeps: list[float] = []
    monkeypatch.setattr("bkam.client._sleep", sleeps.append)
    return sleeps