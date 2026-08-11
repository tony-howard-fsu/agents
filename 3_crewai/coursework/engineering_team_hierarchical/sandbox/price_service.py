"""Price service for retrieving fixed test share prices."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from exceptions import PriceLookupError, UnknownSymbolError

_FIXED_PRICES = {
    "AAPL": 150.00,
    "TSLA": 250.00,
    "GOOGL": 2800.00,
}


def get_share_price(symbol: str) -> float:
    normalized = symbol.upper()
    try:
        return _FIXED_PRICES[normalized]
    except KeyError as exc:
        raise UnknownSymbolError(f"Unsupported symbol: {symbol}") from exc


class PriceService:
    def get_price(self, symbol: str, as_of: datetime | None = None) -> Decimal:
        normalized = symbol.upper()
        try:
            price = get_share_price(normalized)
            return Decimal(str(price))
        except UnknownSymbolError:
            raise
        except Exception as exc:  # pragma: no cover - defensive wrapper
            raise PriceLookupError(f"Could not retrieve price for {symbol}") from exc
