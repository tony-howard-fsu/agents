"""Fixed test prices for known stock symbols."""

from typing import Final

_PRICES: Final[dict[str, float]] = {
    "AAPL": 150.00,
    "TSLA": 250.00,
    "GOOGL": 140.00,
}


def get_share_price(symbol: str) -> float:
    """Returns a fixed test price for a given stock symbol.

    Args:
        symbol: The stock ticker symbol (e.g. "AAPL", "TSLA", "GOOGL").

    Returns:
        The fixed price for the given symbol.

    Raises:
        ValueError: If the symbol is not one of the known test symbols.
    """
    if symbol not in _PRICES:
        raise ValueError(f"Unknown symbol: {symbol}")
    return _PRICES[symbol]
