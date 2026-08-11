import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional


@dataclass(frozen=True)
class Transaction:
    id: str
    type: str                  # "DEPOSIT" | "WITHDRAW" | "BUY" | "SELL"
    symbol: Optional[str]      # None for DEPOSIT/WITHDRAW; ticker for BUY/SELL
    quantity: Optional[int]    # None for DEPOSIT/WITHDRAW
    price: Optional[float]     # None for DEPOSIT/WITHDRAW; per-share price for BUY/SELL
    amount: float              # cash impact: positive = inflow, negative = outflow
    timestamp: datetime
    account_id: str


@dataclass(frozen=True)
class Holding:
    symbol: str
    quantity: int
    avg_cost_per_share: float


class SharePriceService:
    _TEST_PRICES: dict[str, float] = {"AAPL": 150.0, "TSLA": 250.0, "GOOGL": 175.0}

    def get_share_price(self, symbol: str) -> float:
        if symbol not in self._TEST_PRICES:
            raise ValueError(f"Unknown symbol: {symbol}")
        return self._TEST_PRICES[symbol]


class _Account:
    """Internal mutable state class for a single account.

    Not exposed outside backend.py. AccountManager is the only code
    that touches it.
    """

    def __init__(self, account_id: str, name: str, initial_deposit: float) -> None:
        self.id: str = account_id
        self.name: str = name
        self.balance: float = initial_deposit
        self.holdings: dict[str, Holding] = {}          # symbol -> Holding
        self.transactions: list[Transaction] = []
        self.initial_deposit: float = initial_deposit
        self.total_deposited: float = initial_deposit
        self.total_withdrawn: float = 0.0

        # Record the initial DEPOSIT transaction when initial_deposit > 0
        if initial_deposit > 0:
            tx = Transaction(
                id=str(uuid.uuid4()),
                type="DEPOSIT",
                symbol=None,
                quantity=None,
                price=None,
                amount=initial_deposit,
                timestamp=datetime.now(),
                account_id=self.id,
            )
            self.transactions.append(tx)

    # ------------------------------------------------------------------
    # Internal mutation helpers
    # ------------------------------------------------------------------

    def _add_transaction(self, tx: Transaction) -> None:
        self.transactions.append(tx)

    def _apply_deposit(self, amount: float) -> Transaction:
        self.balance += amount
        self.total_deposited += amount
        tx = Transaction(
            id=str(uuid.uuid4()),
            type="DEPOSIT",
            symbol=None,
            quantity=None,
            price=None,
            amount=amount,
            timestamp=datetime.now(),
            account_id=self.id,
        )
        self._add_transaction(tx)
        return tx

    def _apply_withdraw(self, amount: float) -> Transaction:
        self.balance -= amount
        self.total_withdrawn += amount
        tx = Transaction(
            id=str(uuid.uuid4()),
            type="WITHDRAW",
            symbol=None,
            quantity=None,
            price=None,
            amount=-amount,
            timestamp=datetime.now(),
            account_id=self.id,
        )
        self._add_transaction(tx)
        return tx

    def _apply_buy(self, symbol: str, quantity: int, price: float) -> Transaction:
        cost = quantity * price
        self.balance -= cost

        if symbol in self.holdings:
            old = self.holdings[symbol]
            new_qty = old.quantity + quantity
            new_avg = (
                old.quantity * old.avg_cost_per_share + quantity * price
            ) / new_qty
            self.holdings[symbol] = Holding(
                symbol=symbol, quantity=new_qty, avg_cost_per_share=new_avg
            )
        else:
            self.holdings[symbol] = Holding(
                symbol=symbol, quantity=quantity, avg_cost_per_share=price
            )

        tx = Transaction(
            id=str(uuid.uuid4()),
            type="BUY",
            symbol=symbol,
            quantity=quantity,
            price=price,
            amount=-cost,
            timestamp=datetime.now(),
            account_id=self.id,
        )
        self._add_transaction(tx)
        return tx

    def _apply_sell(self, symbol: str, quantity: int, price: float) -> Transaction:
        proceeds = quantity * price
        self.balance += proceeds

        old = self.holdings[symbol]
        new_qty = old.quantity - quantity
        if new_qty == 0:
            del self.holdings[symbol]
        else:
            # avg_cost_per_share remains unchanged
            self.holdings[symbol] = Holding(
                symbol=symbol, quantity=new_qty, avg_cost_per_share=old.avg_cost_per_share
            )

        tx = Transaction(
            id=str(uuid.uuid4()),
            type="SELL",
            symbol=symbol,
            quantity=quantity,
            price=price,
            amount=proceeds,
            timestamp=datetime.now(),
            account_id=self.id,
        )
        self._add_transaction(tx)
        return tx

    # ------------------------------------------------------------------
    # Permission checks
    # ------------------------------------------------------------------

    def _can_withdraw(self, amount: float) -> bool:
        return self.balance >= amount

    def _can_buy(self, quantity: int, price: float) -> bool:
        return self.balance >= quantity * price

    def _can_sell(self, symbol: str, quantity: int) -> bool:
        return symbol in self.holdings and self.holdings[symbol].quantity >= quantity

    # ------------------------------------------------------------------
    # Read-only snapshot helpers
    # ------------------------------------------------------------------

    def _get_portfolio_value(self, price_func) -> float:
        market_value = sum(
            h.quantity * price_func(h.symbol) for h in self.holdings.values()
        )
        return self.balance + market_value

    def _get_profit_loss(self, price_func) -> float:
        market_value = sum(
            h.quantity * price_func(h.symbol) for h in self.holdings.values()
        )
        return (self.balance + market_value) - (
            self.total_deposited - self.total_withdrawn
        )

    def _get_holdings_snapshot(self) -> list[Holding]:
        """Return a copy of all Holding objects.

        Because Holding is frozen, a shallow copy of the values is safe.
        """
        return list(self.holdings.values())

    def _get_transactions_snapshot(self) -> list[Transaction]:
        """Return a copy of the transaction list, most recent first.

        Because Transaction is frozen, a shallow copy is safe.
        """
        return list(reversed(self.transactions))

    def _get_balance(self) -> float:
        return self.balance


class AccountManager:
    """Public API for the Trading Simulation Account Management System.

    This is the ONLY class that should be imported by frontend code.
    """

    def __init__(self, price_service: Optional[SharePriceService] = None) -> None:
        """
        If price_service is None, create a default SharePriceService.
        Initializes empty accounts dict.
        """
        self._accounts: dict[str, _Account] = {}
        if price_service is None:
            self._price_service = SharePriceService()
        else:
            self._price_service = price_service

    # ------------------------------------------------------------------
    # Price look-up (public, so the frontend can use the same instance)
    # ------------------------------------------------------------------

    def get_share_price(self, symbol: str) -> float:
        """Return the current price for *symbol* from the internal price service.

        Raises ValueError if the symbol is unknown.
        """
        return self._price_service.get_share_price(symbol)

    # ------------------------------------------------------------------
    # Account lifecycle
    # ------------------------------------------------------------------

    def create_account(self, name: str, initial_deposit: float = 0.0) -> str:
        """Creates a new _Account. Returns the new account_id (UUID4 string).

        initial_deposit must be >= 0. Creates initial DEPOSIT transaction.

        Raises ValueError if initial_deposit < 0, name is empty, or an
        account with the same name already exists (case-insensitive).
        """
        if not name or not name.strip():
            raise ValueError("Account name must be non-empty.")
        if initial_deposit < 0:
            raise ValueError("Initial deposit must be >= 0.")

        stripped = name.strip()
        # Prevent duplicate names (case-insensitive)
        for account in self._accounts.values():
            if account.name.strip().lower() == stripped.lower():
                raise ValueError(f"An account with the name '{stripped}' already exists.")

        account_id = str(uuid.uuid4())
        self._accounts[account_id] = _Account(account_id, stripped, initial_deposit)
        return account_id

    def get_account_name(self, account_id: str) -> str:
        """Return the name associated with *account_id*.

        Raises:
            KeyError: If *account_id* does not exist.
        """
        self._require_account(account_id)
        return self._accounts[account_id].name

    def list_accounts(self) -> list[dict]:
        """Returns [{"id": ..., "name": ...}, ...] for all accounts."""
        return [
            {"id": a.id, "name": a.name}
            for a in self._accounts.values()
        ]

    # ------------------------------------------------------------------
    # Cash operations
    # ------------------------------------------------------------------

    def deposit(self, account_id: str, amount: float) -> Transaction:
        """Deposit cash into an account.

        Raises:
            KeyError: If *account_id* does not exist.
            ValueError: If *amount* <= 0.
        """
        self._require_account(account_id)
        if amount <= 0:
            raise ValueError("Deposit amount must be > 0.")
        return self._accounts[account_id]._apply_deposit(amount)

    def withdraw(self, account_id: str, amount: float) -> Transaction:
        """Withdraw cash from an account.

        Raises:
            KeyError: If *account_id* does not exist.
            ValueError: If *amount* <= 0 or balance is insufficient.
        """
        self._require_account(account_id)
        if amount <= 0:
            raise ValueError("Withdrawal amount must be > 0.")
        account = self._accounts[account_id]
        if not account._can_withdraw(amount):
            raise ValueError("Insufficient balance.")
        return account._apply_withdraw(amount)

    # ------------------------------------------------------------------
    # Trading operations
    # ------------------------------------------------------------------

    def buy(self, account_id: str, symbol: str, quantity: int) -> Transaction:
        """Buy shares of *symbol*.

        Raises:
            KeyError: If *account_id* does not exist.
            ValueError: If *quantity* <= 0, *symbol* is unknown, or
                        balance is insufficient for the total cost.
        """
        self._require_account(account_id)
        if quantity <= 0:
            raise ValueError("Quantity must be > 0.")
        price = self._price_service.get_share_price(symbol)  # may raise ValueError
        account = self._accounts[account_id]
        if not account._can_buy(quantity, price):
            raise ValueError("Insufficient balance.")
        return account._apply_buy(symbol, quantity, price)

    def sell(self, account_id: str, symbol: str, quantity: int) -> Transaction:
        """Sell shares of *symbol*.

        Raises:
            KeyError: If *account_id* does not exist.
            ValueError: If *quantity* <= 0, *symbol* is unknown, or the
                        account does not hold enough shares.
        """
        self._require_account(account_id)
        if quantity <= 0:
            raise ValueError("Quantity must be > 0.")
        price = self._price_service.get_share_price(symbol)  # may raise ValueError
        account = self._accounts[account_id]
        if not account._can_sell(symbol, quantity):
            raise ValueError("Insufficient holdings.")
        return account._apply_sell(symbol, quantity, price)

    # ------------------------------------------------------------------
    # Query methods (all return copies, never internal references)
    # ------------------------------------------------------------------

    def get_balance(self, account_id: str) -> float:
        """Return the current cash balance."""
        self._require_account(account_id)
        return self._accounts[account_id]._get_balance()

    def get_holdings(self, account_id: str) -> list[Holding]:
        """Return a snapshot of current holdings."""
        self._require_account(account_id)
        return self._accounts[account_id]._get_holdings_snapshot()

    def get_portfolio_value(self, account_id: str) -> float:
        """Return cash + market value of all holdings."""
        self._require_account(account_id)
        return self._accounts[account_id]._get_portfolio_value(
            self._price_service.get_share_price
        )

    def get_profit_loss(self, account_id: str) -> float:
        """Return the account's overall profit/loss."""
        self._require_account(account_id)
        return self._accounts[account_id]._get_profit_loss(
            self._price_service.get_share_price
        )

    def get_transactions(self, account_id: str) -> list[Transaction]:
        """Return transaction history, most recent first."""
        self._require_account(account_id)
        return self._accounts[account_id]._get_transactions_snapshot()

    def get_holdings_with_market_value(self, account_id: str) -> list[dict]:
        """Return holdings enriched with current market data.

        Each dict contains: symbol, quantity, avg_cost, current_price,
        market_value, unrealized_pl.
        """
        self._require_account(account_id)
        account = self._accounts[account_id]
        result: list[dict] = []
        for h in account._get_holdings_snapshot():
            current_price = self._price_service.get_share_price(h.symbol)
            market_value = h.quantity * current_price
            unrealized_pl = market_value - (h.quantity * h.avg_cost_per_share)
            result.append({
                "symbol": h.symbol,
                "quantity": h.quantity,
                "avg_cost": h.avg_cost_per_share,
                "current_price": current_price,
                "market_value": market_value,
                "unrealized_pl": unrealized_pl,
            })
        return result

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _require_account(self, account_id: str) -> None:
        if account_id not in self._accounts:
            raise KeyError(f"Account not found: {account_id}")
