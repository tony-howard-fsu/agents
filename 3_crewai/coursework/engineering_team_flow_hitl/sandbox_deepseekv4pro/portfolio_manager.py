"""
portfolio_manager.py — Core business logic for a trading simulation
account management system.

Provides enums, data classes, a share-price-provider abstraction,
the AccountManager service, and module-level convenience functions.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class TransactionType(str, Enum):
    """Well-known transaction types (lowercase values as per design spec)."""
    DEPOSIT = "deposit"
    WITHDRAW = "withdraw"
    BUY = "buy"
    SELL = "sell"


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class Transaction:
    """Represents a single monetary or trading transaction on an account."""

    transaction_id: str
    transaction_type: TransactionType
    symbol: Optional[str]
    quantity: Optional[int]
    price_per_share: Optional[float]
    amount: float
    timestamp: datetime
    account_id: str

    # ---- factories --------------------------------------------------------

    @classmethod
    def create_deposit(
        cls, amount: float, account_id: str
    ) -> "Transaction":
        """Factory for DEPOSIT transactions."""
        return cls(
            transaction_id=str(uuid.uuid4()),
            transaction_type=TransactionType.DEPOSIT,
            symbol=None,
            quantity=None,
            price_per_share=None,
            amount=amount,
            timestamp=datetime.now(timezone.utc),
            account_id=account_id,
        )

    @classmethod
    def create_withdrawal(
        cls, amount: float, account_id: str
    ) -> "Transaction":
        """Factory for WITHDRAW transactions."""
        return cls(
            transaction_id=str(uuid.uuid4()),
            transaction_type=TransactionType.WITHDRAW,
            symbol=None,
            quantity=None,
            price_per_share=None,
            amount=amount,
            timestamp=datetime.now(timezone.utc),
            account_id=account_id,
        )

    @classmethod
    def create_buy(
        cls,
        symbol: str,
        quantity: int,
        price_per_share: float,
        account_id: str,
    ) -> "Transaction":
        """Factory for BUY transactions."""
        return cls(
            transaction_id=str(uuid.uuid4()),
            transaction_type=TransactionType.BUY,
            symbol=symbol,
            quantity=quantity,
            price_per_share=price_per_share,
            amount=quantity * price_per_share,
            timestamp=datetime.now(timezone.utc),
            account_id=account_id,
        )

    @classmethod
    def create_sell(
        cls,
        symbol: str,
        quantity: int,
        price_per_share: float,
        account_id: str,
    ) -> "Transaction":
        """Factory for SELL transactions."""
        return cls(
            transaction_id=str(uuid.uuid4()),
            transaction_type=TransactionType.SELL,
            symbol=symbol,
            quantity=quantity,
            price_per_share=price_per_share,
            amount=quantity * price_per_share,
            timestamp=datetime.now(timezone.utc),
            account_id=account_id,
        )

    # ---- serialisation ----------------------------------------------------

    def to_dict(self) -> Dict[str, Any]:
        """Convert this transaction to a JSON-friendly dictionary."""
        return {
            "transaction_id": self.transaction_id,
            "transaction_type": self.transaction_type.value,
            "symbol": self.symbol,
            "quantity": self.quantity,
            "price_per_share": self.price_per_share,
            "amount": self.amount,
            "timestamp": self.timestamp.isoformat(),
            "account_id": self.account_id,
        }

    @staticmethod
    def from_dict(data: Dict[str, Any]) -> "Transaction":
        """Reconstruct a Transaction from a dictionary (inverse of *to_dict*)."""
        return Transaction(
            transaction_id=data["transaction_id"],
            transaction_type=TransactionType(data["transaction_type"]),
            symbol=data.get("symbol"),
            quantity=data.get("quantity"),
            price_per_share=data.get("price_per_share"),
            amount=data["amount"],
            timestamp=datetime.fromisoformat(data["timestamp"]),
            account_id=data["account_id"],
        )


@dataclass
class Account:
    """Represents a single user account within the simulation."""

    account_id: str
    name: str
    balance: float = 0.0
    holdings: Dict[str, int] = field(default_factory=dict)
    transactions: List[Transaction] = field(default_factory=list)
    initial_deposit: float = 0.0
    total_deposited: float = 0.0
    total_withdrawn: float = 0.0
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    # ---- serialisation ----------------------------------------------------

    def to_dict(self) -> Dict[str, Any]:
        """Return a lightweight summary dictionary for this account."""
        return {
            "account_id": self.account_id,
            "name": self.name,
            "balance": self.balance,
            "holdings": dict(self.holdings),
            "transaction_count": len(self.transactions),
            "initial_deposit": self.initial_deposit,
            "total_deposited": self.total_deposited,
            "total_withdrawn": self.total_withdrawn,
            "created_at": self.created_at.isoformat(),
        }

    @staticmethod
    def from_dict(data: Dict[str, Any]) -> "Account":
        """Reconstruct an Account from a dictionary."""
        return Account(
            account_id=data["account_id"],
            name=data["name"],
            balance=data.get("balance", 0.0),
            holdings=data.get("holdings", {}),
            transactions=[],  # transactions are rebuilt by the manager
            initial_deposit=data.get("initial_deposit", 0.0),
            total_deposited=data.get("total_deposited", 0.0),
            total_withdrawn=data.get("total_withdrawn", 0.0),
            created_at=(
                datetime.fromisoformat(data["created_at"])
                if "created_at" in data
                else datetime.now(timezone.utc)
            ),
        )


# ---------------------------------------------------------------------------
# Share-price provider abstraction
# ---------------------------------------------------------------------------

class SharePriceProvider:
    """Abstract base for share-price lookups.

    Subclasses must implement ``get_share_price(symbol: str) -> float``.
    """

    def get_share_price(self, symbol: str) -> float:
        """Return the current price for *symbol*.

        Raises:
            NotImplementedError: Always — must be overridden.
        """
        raise NotImplementedError(
            "SharePriceProvider subclasses must implement get_share_price()"
        )


class TestSharePriceProvider(SharePriceProvider):
    """A provider that returns fixed prices, with optional custom overrides."""

    _DEFAULT_PRICES: Dict[str, float] = {
        "AAPL": 150.0,
        "TSLA": 250.0,
        "GOOGL": 2800.0,
    }

    def __init__(self, prices: Optional[dict[str, float]] = None) -> None:
        """Initialise the provider with optional custom price overrides.

        Args:
            prices: An optional dictionary mapping uppercase symbol
                strings to their fixed prices.  Any symbol not provided
                here falls back to the class-level ``_DEFAULT_PRICES``.
        """
        self._prices: Dict[str, float] = dict(self._DEFAULT_PRICES)
        if prices:
            self._prices.update({k.upper(): v for k, v in prices.items()})

    def get_share_price(self, symbol: str) -> float:
        """Return the current price for *symbol*.

        Raises:
            ValueError: If *symbol* is not known.
        """
        upper = symbol.upper()
        if upper not in self._prices:
            raise ValueError(
                f"Unknown symbol: '{symbol}'. Known symbols: "
                f"{sorted(self._prices.keys())}"
            )
        return self._prices[upper]


# ---------------------------------------------------------------------------
# Account manager service
# ---------------------------------------------------------------------------

class AccountManager:
    """Manages a collection of simulation accounts and their transactions."""

    def __init__(self, price_provider: Optional[SharePriceProvider] = None) -> None:
        """Create an account manager with an optional share-price provider.

        Args:
            price_provider: The ``SharePriceProvider`` to use for valuing
                holdings and executing trades.  Defaults to a fresh
                ``TestSharePriceProvider`` instance when ``None``.
        """
        self._accounts: Dict[str, Account] = {}
        self.price_provider: SharePriceProvider = (
            price_provider if price_provider is not None
            else TestSharePriceProvider()
        )

    # -- account CRUD -------------------------------------------------------

    def create_account(self, name: str, initial_deposit: float = 0.0) -> Account:
        """Create a new account and return it.

        Args:
            name: A human-readable name for the account.
            initial_deposit: The initial cash deposited (must be >= 0).

        Returns:
            The newly-created Account.

        Raises:
            ValueError: If *name* is empty or *initial_deposit* is negative.
        """
        if not name or not name.strip():
            raise ValueError("Account name must not be empty.")
        if initial_deposit < 0:
            raise ValueError("Initial deposit must be >= 0.")

        account_id = str(uuid.uuid4())
        account = Account(
            account_id=account_id,
            name=name.strip(),
            balance=initial_deposit,
            initial_deposit=initial_deposit,
            total_deposited=initial_deposit,
        )

        if initial_deposit > 0:
            txn = Transaction.create_deposit(initial_deposit, account_id)
            account.transactions.append(txn)

        self._accounts[account_id] = account
        return account

    def get_account(self, account_id: str) -> Account:
        """Look up an account by its identifier.

        Args:
            account_id: The UUID string of the account.

        Returns:
            The matching Account.

        Raises:
            KeyError: If no account with *account_id* exists.
        """
        if account_id not in self._accounts:
            raise KeyError(f"Account '{account_id}' not found.")
        return self._accounts[account_id]

    def delete_account(self, account_id: str) -> None:
        """Permanently delete an account.

        Args:
            account_id: The UUID string of the account.

        Raises:
            KeyError: If no account with *account_id* exists.
        """
        if account_id not in self._accounts:
            raise KeyError(f"Account '{account_id}' not found.")
        del self._accounts[account_id]

    def list_accounts(self) -> List[Account]:
        """Return every account currently managed, in an arbitrary order."""
        return list(self._accounts.values())

    # -- cash operations ----------------------------------------------------

    def deposit(self, account_id: str, amount: float) -> Transaction:
        """Deposit cash into an account.

        Args:
            account_id: The UUID string of the account.
            amount: The amount to deposit (must be > 0).

        Returns:
            The deposit Transaction.

        Raises:
            KeyError: If *account_id* is not found.
            ValueError: If *amount* <= 0.
        """
        if amount <= 0:
            raise ValueError("Deposit amount must be positive.")

        account = self.get_account(account_id)
        account.balance += amount
        account.total_deposited += amount

        txn = Transaction.create_deposit(amount, account_id)
        account.transactions.append(txn)
        return txn

    def withdraw(self, account_id: str, amount: float) -> Transaction:
        """Withdraw cash from an account.

        Args:
            account_id: The UUID string of the account.
            amount: The amount to withdraw (must be > 0 and <= balance).

        Returns:
            The withdrawal Transaction.

        Raises:
            KeyError: If *account_id* is not found.
            ValueError: If *amount* <= 0 or > available balance.
        """
        if amount <= 0:
            raise ValueError("Withdrawal amount must be positive.")

        account = self.get_account(account_id)
        self._validate_balance_for_withdrawal(account, amount)

        account.balance -= amount
        account.total_withdrawn += amount

        txn = Transaction.create_withdrawal(amount, account_id)
        account.transactions.append(txn)
        return txn

    # -- trading operations -------------------------------------------------

    def buy_shares(
        self,
        account_id: str,
        symbol: str,
        quantity: int,
    ) -> Transaction:
        """Buy *quantity* shares of *symbol* at the current market price.

        Uses the stored ``self.price_provider`` to obtain prices.

        Args:
            account_id: The UUID string of the account.
            symbol: The ticker symbol (e.g. "AAPL").
            quantity: Number of whole shares to purchase (> 0).

        Returns:
            The BUY Transaction.

        Raises:
            KeyError: If *account_id* is not found.
            ValueError: If *quantity* <= 0 or insufficient funds.
        """
        if quantity <= 0:
            raise ValueError("Quantity must be positive.")

        account = self.get_account(account_id)
        price = self.price_provider.get_share_price(symbol)
        cost = quantity * price

        self._validate_balance_for_purchase(account, cost)

        account.balance -= cost
        sym = symbol.upper()
        account.holdings[sym] = account.holdings.get(sym, 0) + quantity

        txn = Transaction.create_buy(sym, quantity, price, account_id)
        account.transactions.append(txn)
        return txn

    def sell_shares(
        self,
        account_id: str,
        symbol: str,
        quantity: int,
    ) -> Transaction:
        """Sell *quantity* shares of *symbol* at the current market price.

        Uses the stored ``self.price_provider`` to obtain prices.

        Args:
            account_id: The UUID string of the account.
            symbol: The ticker symbol (e.g. "AAPL").
            quantity: Number of whole shares to sell (> 0).

        Returns:
            The SELL Transaction.

        Raises:
            KeyError: If *account_id* is not found.
            ValueError: If *quantity* <= 0 or insufficient holdings.
        """
        if quantity <= 0:
            raise ValueError("Quantity must be positive.")

        account = self.get_account(account_id)
        sym = symbol.upper()

        self._validate_holdings_for_sale(account, sym, quantity)

        price = self.price_provider.get_share_price(sym)
        proceeds = quantity * price

        account.balance += proceeds
        account.holdings[sym] = account.holdings.get(sym, 0) - quantity

        # Remove zero-balance symbols to keep holdings clean.
        if account.holdings[sym] == 0:
            del account.holdings[sym]

        txn = Transaction.create_sell(sym, quantity, price, account_id)
        account.transactions.append(txn)
        return txn

    # -- queries ------------------------------------------------------------

    def get_holdings(self, account_id: str) -> Dict[str, int]:
        """Return the non-zero holdings dictionary for *account_id*.

        Only symbols with a quantity > 0 are included.
        """
        account = self.get_account(account_id)
        return {sym: qty for sym, qty in account.holdings.items() if qty > 0}

    def get_portfolio_value(self, account_id: str) -> float:
        """Calculate the total value (cash + market value of holdings).

        Uses the stored ``self.price_provider`` for pricing.

        Args:
            account_id: The UUID string of the account.

        Returns:
            The portfolio value as a float.
        """
        account = self.get_account(account_id)
        holdings_value = sum(
            qty * self.price_provider.get_share_price(sym)
            for sym, qty in account.holdings.items()
        )
        return account.balance + holdings_value

    def get_profit_loss(self, account_id: str) -> float:
        """Return the total profit/loss for *account_id*.

        Uses the stored ``self.price_provider`` for portfolio valuation.

        Formula:
            (current portfolio value + total withdrawn) - total deposited.
        """
        account = self.get_account(account_id)
        portfolio_value = self.get_portfolio_value(account_id)
        return (portfolio_value + account.total_withdrawn) - account.total_deposited

    def get_transactions(self, account_id: str) -> List[Transaction]:
        """Return a chronologically-ordered list of transactions for an account."""
        account = self.get_account(account_id)
        return list(account.transactions)

    def get_transactions_filtered(
        self,
        account_id: str,
        transaction_type: Optional[str] = None,
        symbol: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
    ) -> list[Transaction]:
        """Return filtered transactions for *account_id*.

        Args:
            account_id: The UUID string of the account.
            transaction_type: If given, only include transactions of this
                type (one of ``"deposit"``, ``"withdraw"``, ``"buy"``,
                ``"sell"``, or a ``TransactionType`` value).
            symbol: If given, only include transactions for this symbol
                (case-insensitive comparison).
            start_time: If given, only include transactions at or after
                this timestamp.
            end_time: If given, only include transactions at or before
                this timestamp.

        Returns:
            A (possibly empty) list of matching ``Transaction`` objects.
        """
        account = self.get_account(account_id)
        results: list[Transaction] = list(account.transactions)

        if transaction_type is not None:
            # Accept both string and TransactionType values.
            if isinstance(transaction_type, TransactionType):
                ttype = transaction_type
            else:
                ttype = TransactionType(transaction_type)
            results = [t for t in results if t.transaction_type == ttype]

        if symbol is not None:
            sym_upper = symbol.upper()
            results = [
                t for t in results
                if t.symbol is not None and t.symbol.upper() == sym_upper
            ]

        if start_time is not None:
            results = [t for t in results if t.timestamp >= start_time]

        if end_time is not None:
            results = [t for t in results if t.timestamp <= end_time]

        return results

    def get_account_summary(self, account_id: str) -> dict:
        """Return a summary dictionary for *account_id*.

        Keys:
            account_id, name, balance, holdings, portfolio_value,
            profit_loss, total_deposited, total_withdrawn,
            transaction_count.
        """
        account = self.get_account(account_id)
        return {
            "account_id": account.account_id,
            "name": account.name,
            "balance": account.balance,
            "holdings": dict(account.holdings),
            "portfolio_value": self.get_portfolio_value(account_id),
            "profit_loss": self.get_profit_loss(account_id),
            "total_deposited": account.total_deposited,
            "total_withdrawn": account.total_withdrawn,
            "transaction_count": len(account.transactions),
        }

    def get_all_account_summaries(self) -> list[dict]:
        """Return a list of summary dicts for every managed account."""
        return [self.get_account_summary(acct.account_id) for acct in self._accounts.values()]

    # -- internal validation helpers ----------------------------------------

    def _validate_balance_for_withdrawal(self, account: Account, amount: float) -> None:
        """Raise ``ValueError`` if *amount* exceeds the account balance."""
        if amount > account.balance:
            raise ValueError(
                f"Insufficient funds: tried to withdraw {amount}, "
                f"but balance is {account.balance}."
            )

    def _validate_balance_for_purchase(self, account: Account, total_cost: float) -> None:
        """Raise ``ValueError`` if *total_cost* exceeds the account balance."""
        if total_cost > account.balance:
            raise ValueError(
                f"Insufficient funds: purchase requires {total_cost}, "
                f"but balance is {account.balance}."
            )

    def _validate_holdings_for_sale(
        self, account: Account, symbol: str, quantity: int
    ) -> None:
        """Raise ``ValueError`` if *quantity* exceeds the held shares of *symbol*."""
        current_holding = account.holdings.get(symbol, 0)
        if quantity > current_holding:
            raise ValueError(
                f"Insufficient holdings: tried to sell {quantity} "
                f"of {symbol}, but only {current_holding} held."
            )


# ---------------------------------------------------------------------------
# Module-level convenience
# ---------------------------------------------------------------------------

_default_manager: Optional[AccountManager] = None


def get_default_manager() -> AccountManager:
    """Return (and lazily create) the module-level AccountManager singleton."""
    global _default_manager
    if _default_manager is None:
        _default_manager = AccountManager()
    return _default_manager


def reset_manager() -> None:
    """Discard the current default manager so a fresh one is used next time."""
    global _default_manager
    _default_manager = None
