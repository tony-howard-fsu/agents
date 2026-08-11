"""Domain models for the trading simulation backend."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

TRANSACTION_TYPE_DEPOSIT: str = "DEPOSIT"
TRANSACTION_TYPE_WITHDRAWAL: str = "WITHDRAWAL"
TRANSACTION_TYPE_BUY: str = "BUY"
TRANSACTION_TYPE_SELL: str = "SELL"


@dataclass(frozen=True)
class Transaction:
    transaction_id: str
    account_id: str
    sequence: int
    transaction_type: str
    timestamp: datetime
    cash_delta: Decimal
    symbol: str | None
    quantity: Decimal | None
    execution_price: Decimal | None
    notes: str | None


@dataclass
class Account:
    account_id: str
    owner_name: str
    created_at: datetime
    initial_deposit: Decimal
    next_sequence: int
    transactions: list[Transaction]


@dataclass(frozen=True)
class Holding:
    symbol: str
    quantity: Decimal


@dataclass(frozen=True)
class PositionValuation:
    symbol: str
    quantity: Decimal
    price: Decimal
    market_value: Decimal


@dataclass(frozen=True)
class PortfolioValuation:
    account_id: str
    as_of: datetime | None
    cash_balance: Decimal
    positions: list[PositionValuation]
    securities_value: Decimal
    total_value: Decimal
    net_external_contributions: Decimal
    profit_loss: Decimal
