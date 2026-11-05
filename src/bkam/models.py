from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

class BanknoteRate(BaseModel):
    """Exchange rate for foreign banknotes, as published by Bank Al-Maghrib"""

    model_config = ConfigDict(frozen=True, populate_by_name=True)

    currency: str = Field(alias="libDevise")
    unit: int = Field(alias="uniteDevise", gt= 0)
    buy: Decimal = Field(alias="achatClientele")
    sell: Decimal = Field(alias="venteClientele")
    published_at: datetime = Field(alias="date")

    @property
    def buy_per_unit(self) -> Decimal:
        return self.buy / self.unit

    @property
    def sell_per_unit(self) -> Decimal:
        return self.sell / self.unit


class TransferRate(BaseModel):
    """Average exchange rate used for bank transfers (virements)."""

    model_config = ConfigDict(frozen=True, populate_by_name=True)

    currency: str = Field(alias="libDevise")
    unit: int = Field(alias="uniteDevise", gt= 0)
    average: Decimal = Field(alias="moyen")
    published_at: datetime = Field(alias="date")

    @property
    def average_per_unit(self) -> Decimal:
        return self.average / self.unit

    