"""Domain-specific exceptions for the trading simulation backend."""

from __future__ import annotations


class TradingAppError(Exception):
    """Base exception for all expected application errors."""


class ValidationError(TradingAppError):
    """Raised when user input is invalid."""


class AccountNotFoundError(TradingAppError):
    """Raised when an account ID does not exist."""


class InsufficientFundsError(TradingAppError):
    """Raised when a withdrawal or buy would exceed available cash."""


class InsufficientHoldingsError(TradingAppError):
    """Raised when a sell quantity exceeds available holdings."""


class UnknownSymbolError(TradingAppError):
    """Raised when a requested share symbol is unsupported."""


class PriceLookupError(TradingAppError):
    """Raised when a price cannot be retrieved."""
