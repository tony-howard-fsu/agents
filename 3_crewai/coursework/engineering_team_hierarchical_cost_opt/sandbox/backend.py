"""Account Management System - Core Backend Module.

Provides data structures, custom exceptions, and the Account/AccountManager
classes for managing trading simulation accounts entirely in memory.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Callable, Dict, List, Optional
import uuid


# ---------------------------------------------------------------------------
# Data Structures
# ---------------------------------------------------------------------------

@dataclass
class Transaction:
    """Represents a single financial event (deposit, withdrawal, buy, sell).

    Attributes:
        type: One of ``"DEPOSIT"``, ``"WITHDRAW"``, ``"BUY"``, ``"SELL"``.
        symbol: Stock ticker; empty string for cash transactions.
        quantity: Number of shares; 0 for cash transactions.
        price: Price per share at the time of the transaction; 0 for cash
            transactions.
        amount: Cash amount.  For trades this equals ``quantity * price``.
        timestamp: UTC time when the transaction was recorded.
    """
    type: str
    symbol: str = ""
    quantity: float = 0.0
    price: float = 0.0
    amount: float = 0.0
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class Holding:
    """Snapshot of a stock position held in an account.

    Attributes:
        symbol: Stock ticker.
        quantity: Number of shares owned.
    """
    symbol: str
    quantity: float


# ---------------------------------------------------------------------------
# Custom Exceptions
# ---------------------------------------------------------------------------

class InsufficientFundsError(Exception):
    """Raised when a cash operation exceeds the available balance."""


class InsufficientSharesError(Exception):
    """Raised when a sell order exceeds the currently held shares."""


# ---------------------------------------------------------------------------
# Internal Account Class
# ---------------------------------------------------------------------------

class Account:
    """Internal (private) class representing a single trading account.

    Maintains cash balance, holdings, an append-only transaction log, and
    the initial deposit used for P&L calculations.
    """

    def __init__(self, account_id: str, initial_deposit: float) -> None:
        """Initialise an account.

        Args:
            account_id: Unique identifier for this account.
            initial_deposit: Opening cash deposit (must be >= 0).
        """
        self.account_id: str = account_id
        self.cash_balance: float = initial_deposit
        self.holdings: Dict[str, float] = {}
        self.initial_deposit: float = initial_deposit
        self.transactions: List[Transaction] = []

        # Log the initial deposit as a transaction if non-zero.
        if initial_deposit > 0:
            self.transactions.append(
                Transaction(
                    type="DEPOSIT",
                    amount=initial_deposit,
                )
            )

    # -- Cash operations ----------------------------------------------------

    def deposit(self, amount: float) -> None:
        """Add cash to the account.

        Args:
            amount: Must be > 0.

        Raises:
            ValueError: If *amount* is <= 0.
        """
        if amount <= 0:
            raise ValueError("Deposit amount must be positive.")
        self.cash_balance += amount
        self.transactions.append(
            Transaction(type="DEPOSIT", amount=amount)
        )

    def withdraw(self, amount: float) -> None:
        """Remove cash from the account.

        Args:
            amount: Must be > 0 and <= current ``cash_balance``.

        Raises:
            ValueError: If *amount* is <= 0.
            InsufficientFundsError: If *amount* exceeds ``cash_balance``.
        """
        if amount <= 0:
            raise ValueError("Withdrawal amount must be positive.")
        if amount > self.cash_balance:
            raise InsufficientFundsError(
                f"Insufficient funds: tried to withdraw {amount}, "
                f"but balance is {self.cash_balance}."
            )
        self.cash_balance -= amount
        self.transactions.append(
            Transaction(type="WITHDRAW", amount=amount)
        )

    # -- Trade operations ---------------------------------------------------

    def buy(self, symbol: str, quantity: float, price: float) -> None:
        """Purchase shares of a stock.

        Args:
            symbol: Stock ticker.
            quantity: Number of shares to buy.
            price: Current price per share.

        Raises:
            InsufficientFundsError: If ``quantity * price`` exceeds
                ``cash_balance``.
        """
        cost = quantity * price
        if cost > self.cash_balance:
            raise InsufficientFundsError(
                f"Insufficient funds: buy cost {cost}, "
                f"cash balance {self.cash_balance}."
            )
        self.cash_balance -= cost
        self.holdings[symbol] = self.holdings.get(symbol, 0.0) + quantity
        self.transactions.append(
            Transaction(
                type="BUY",
                symbol=symbol,
                quantity=quantity,
                price=price,
                amount=cost,
            )
        )

    def sell(self, symbol: str, quantity: float, price: float) -> None:
        """Sell shares of a stock.

        Args:
            symbol: Stock ticker.
            quantity: Number of shares to sell.
            price: Current price per share.

        Raises:
            InsufficientSharesError: If *quantity* exceeds the currently
                held quantity for *symbol*.
        """
        current_qty = self.holdings.get(symbol, 0.0)
        if quantity > current_qty:
            raise InsufficientSharesError(
                f"Insufficient shares: tried to sell {quantity} "
                f"of {symbol}, but only hold {current_qty}."
            )
        proceeds = quantity * price
        self.cash_balance += proceeds
        new_qty = current_qty - quantity
        if new_qty == 0:
            del self.holdings[symbol]
        else:
            self.holdings[symbol] = new_qty
        self.transactions.append(
            Transaction(
                type="SELL",
                symbol=symbol,
                quantity=quantity,
                price=price,
                amount=proceeds,
            )
        )

    # -- Reporting methods --------------------------------------------------

    def get_portfolio_value(self, price_provider: Callable[[str], float]) -> float:
        """Compute total portfolio value (cash + market value of holdings).

        Args:
            price_provider: Callable that returns the current price for a
                given symbol.

        Returns:
            The sum of cash balance and the mark-to-market value of all
            holdings.
        """
        holdings_value = sum(
            qty * price_provider(symbol)
            for symbol, qty in self.holdings.items()
        )
        return self.cash_balance + holdings_value

    def get_profit_loss(self, price_provider: Callable[[str], float]) -> float:
        """Compute profit/loss relative to the initial deposit.

        P&L is defined as ``portfolio_value - initial_deposit``.

        Args:
            price_provider: Callable that returns the current price for a
                given symbol.

        Returns:
            The difference between current portfolio value and the initial
            deposit.
        """
        return self.get_portfolio_value(price_provider) - self.initial_deposit

    def get_holdings_report(self) -> List[Holding]:
        """Return a list of ``Holding`` objects for all non-zero positions."""
        return [
            Holding(symbol=sym, quantity=qty)
            for sym, qty in self.holdings.items()
            if qty != 0.0
        ]

    def get_transaction_history(self) -> List[Transaction]:
        """Return the full append-only transaction log."""
        return list(self.transactions)


# ---------------------------------------------------------------------------
# AccountManager - Public API
# ---------------------------------------------------------------------------

class AccountManager:
    """Public API for managing multiple trading accounts.

    The manager holds a dictionary of ``Account`` objects keyed by their
    unique account ID and uses an injected price-provider callable to
    resolve current share prices.

    Typical usage::

        manager = AccountManager()          # uses default price provider
        acc_id = manager.create_account(1000.0)
        manager.record_trade(acc_id, "BUY", "AAPL", 10)
        print(manager.get_portfolio_value(acc_id))
    """

    def __init__(
        self,
        price_provider: Optional[Callable[[str], float]] = None,
    ) -> None:
        """Create an AccountManager.

        Args:
            price_provider: A callable ``f(symbol: str) -> float`` that
                returns the current share price.  If ``None``, the default
                ``get_share_price`` from ``share_prices`` is imported and
                used.
        """
        if price_provider is None:
            from share_prices import get_share_price  # type: ignore[import-not-found]
            self.price_provider: Callable[[str], float] = get_share_price
        else:
            self.price_provider = price_provider

        self._accounts: Dict[str, Account] = {}

    # -- Account lifecycle --------------------------------------------------

    def create_account(self, initial_deposit: float = 0.0) -> str:
        """Create a new account with an optional initial deposit.

        Args:
            initial_deposit: Non-negative cash amount to seed the account.

        Returns:
            The unique account ID (UUID string).

        Raises:
            ValueError: If *initial_deposit* is negative.
        """
        if initial_deposit < 0:
            raise ValueError("Initial deposit cannot be negative.")
        account_id = str(uuid.uuid4())
        self._accounts[account_id] = Account(account_id, initial_deposit)
        return account_id

    # -- Cash operations ----------------------------------------------------

    def _get_account(self, account_id: str) -> Account:
        """Retrieve an account by ID, raising ``KeyError`` if missing."""
        if account_id not in self._accounts:
            raise KeyError(f"Account '{account_id}' not found.")
        return self._accounts[account_id]

    def deposit(self, account_id: str, amount: float) -> None:
        """Add cash to an existing account.

        Args:
            account_id: The target account ID.
            amount: Positive cash amount to deposit.

        Raises:
            KeyError: If *account_id* is not found.
            ValueError: If *amount* <= 0.
        """
        self._get_account(account_id).deposit(amount)

    def withdraw(self, account_id: str, amount: float) -> None:
        """Remove cash from an existing account.

        Args:
            account_id: The target account ID.
            amount: Positive cash amount to withdraw.

        Raises:
            KeyError: If *account_id* is not found.
            ValueError: If *amount* <= 0.
            InsufficientFundsError: If *amount* exceeds the account's cash
                balance.
        """
        self._get_account(account_id).withdraw(amount)

    # -- Trade recording ----------------------------------------------------

    def record_trade(
        self,
        account_id: str,
        trade_type: str,
        symbol: str,
        quantity: float,
    ) -> None:
        """Record a BUY or SELL trade for an account.

        The current price is obtained via ``self.price_provider(symbol)``.

        Args:
            account_id: The target account ID.
            trade_type: Either ``"BUY"`` or ``"SELL"``.
            symbol: Stock ticker.
            quantity: Number of shares to trade.

        Raises:
            KeyError: If *account_id* is not found.
            ValueError: If the price provider raises one (e.g. unknown
                symbol), or if *trade_type* is not ``"BUY"`` / ``"SELL"``.
            InsufficientFundsError: For a BUY when cash is insufficient.
            InsufficientSharesError: For a SELL when holdings are
                insufficient.
        """
        account = self._get_account(account_id)
        price = self.price_provider(symbol)

        trade_type = trade_type.upper()
        if trade_type == "BUY":
            account.buy(symbol, quantity, price)
        elif trade_type == "SELL":
            account.sell(symbol, quantity, price)
        else:
            raise ValueError(
                f"Unknown trade_type '{trade_type}'; expected 'BUY' or 'SELL'."
            )

    # -- Reporting ----------------------------------------------------------

    def get_portfolio_value(self, account_id: str) -> float:
        """Return the total portfolio value for an account.

        Equals cash + mark-to-market value of all holdings.
        """
        return self._get_account(account_id).get_portfolio_value(
            self.price_provider
        )

    def get_profit_loss(self, account_id: str) -> float:
        """Return the profit/loss for an account.

        Defined as ``portfolio_value - initial_deposit``.
        """
        return self._get_account(account_id).get_profit_loss(
            self.price_provider
        )

    def get_holdings_report(self, account_id: str) -> List[Holding]:
        """Return a list of ``Holding`` objects for non-zero positions."""
        return self._get_account(account_id).get_holdings_report()

    def get_pnl_report(self, account_id: str) -> float:
        """Alias for :meth:`get_profit_loss`."""
        return self.get_profit_loss(account_id)

    def get_transaction_history(self, account_id: str) -> List[Transaction]:
        """Return the full chronological transaction log for an account."""
        return self._get_account(account_id).get_transaction_history()
