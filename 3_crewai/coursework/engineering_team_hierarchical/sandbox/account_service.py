"""Business logic for managing trading simulation accounts."""

from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timezone
from decimal import Decimal
from threading import Lock
from uuid import uuid4

from exceptions import (
    InsufficientFundsError,
    InsufficientHoldingsError,
    PriceLookupError,
    ValidationError,
)
from models import (
    Account,
    Holding,
    PortfolioValuation,
    PositionValuation,
    Transaction,
    TRANSACTION_TYPE_BUY,
    TRANSACTION_TYPE_DEPOSIT,
    TRANSACTION_TYPE_SELL,
    TRANSACTION_TYPE_WITHDRAWAL,
)
from price_service import PriceService
from repository import InMemoryAccountRepository


class AccountService:
    def __init__(self, repository: InMemoryAccountRepository, price_service: PriceService) -> None:
        self._repository = repository
        self._price_service = price_service
        self._lock = Lock()

    def create_account(self, owner_name: str, initial_deposit: Decimal, timestamp: datetime | None = None) -> Account:
        self._validate_account_owner_name(owner_name)
        self._validate_non_negative_amount(initial_deposit, "initial_deposit")
        effective_timestamp = self._get_effective_timestamp(timestamp)
        with self._lock:
            account = Account(
                account_id=str(uuid4()),
                owner_name=owner_name.strip(),
                created_at=effective_timestamp,
                initial_deposit=initial_deposit,
                next_sequence=1,
                transactions=[],
            )
            self._repository.add_account(account)
            if initial_deposit > 0:
                self._create_transaction(account, TRANSACTION_TYPE_DEPOSIT, effective_timestamp, initial_deposit, None, None, None, "Initial deposit")
            return account

    def get_account(self, account_id: str) -> Account:
        return self._repository.get_account(account_id)

    def list_accounts(self) -> list[Account]:
        return self._repository.list_accounts()

    def deposit(self, account_id: str, amount: Decimal, timestamp: datetime | None = None, notes: str | None = None) -> Transaction:
        self._validate_positive_amount(amount, "amount")
        with self._lock:
            account = self.get_account(account_id)
            return self._create_transaction(account, TRANSACTION_TYPE_DEPOSIT, self._get_effective_timestamp(timestamp), amount, None, None, None, notes)

    def withdraw(self, account_id: str, amount: Decimal, timestamp: datetime | None = None, notes: str | None = None) -> Transaction:
        self._validate_positive_amount(amount, "amount")
        with self._lock:
            account = self.get_account(account_id)
            if self.get_cash_balance(account_id) < amount:
                raise InsufficientFundsError("Insufficient cash for withdrawal")
            return self._create_transaction(account, TRANSACTION_TYPE_WITHDRAWAL, self._get_effective_timestamp(timestamp), -amount, None, None, None, notes)

    def buy_shares(self, account_id: str, symbol: str, quantity: Decimal, timestamp: datetime | None = None, notes: str | None = None) -> Transaction:
        symbol = self._normalize_symbol(symbol)
        self._validate_positive_quantity(quantity)
        with self._lock:
            account = self.get_account(account_id)
            price = self._price_service.get_price(symbol, timestamp)
            cost = quantity * price
            if self.get_cash_balance(account_id) < cost:
                raise InsufficientFundsError("Insufficient cash for purchase")
            return self._create_transaction(account, TRANSACTION_TYPE_BUY, self._get_effective_timestamp(timestamp), -cost, symbol, quantity, price, notes)

    def sell_shares(self, account_id: str, symbol: str, quantity: Decimal, timestamp: datetime | None = None, notes: str | None = None) -> Transaction:
        symbol = self._normalize_symbol(symbol)
        self._validate_positive_quantity(quantity)
        with self._lock:
            account = self.get_account(account_id)
            holdings = self._calculate_holdings_from_transactions(account.transactions)
            if holdings.get(symbol, Decimal("0")) < quantity:
                raise InsufficientHoldingsError("Insufficient holdings for sale")
            price = self._price_service.get_price(symbol, timestamp)
            proceeds = quantity * price
            return self._create_transaction(account, TRANSACTION_TYPE_SELL, self._get_effective_timestamp(timestamp), proceeds, symbol, quantity, price, notes)

    def get_cash_balance(self, account_id: str, as_of: datetime | None = None) -> Decimal:
        account = self.get_account(account_id)
        transactions = self._filter_transactions_as_of(account.transactions, as_of)
        return self._calculate_cash_balance_from_transactions(transactions)

    def get_holdings(self, account_id: str, as_of: datetime | None = None) -> list[Holding]:
        account = self.get_account(account_id)
        transactions = self._filter_transactions_as_of(account.transactions, as_of)
        holdings = self._calculate_holdings_from_transactions(transactions)
        return [Holding(symbol=s, quantity=q) for s, q in sorted(holdings.items()) if q > 0]

    def get_portfolio_valuation(self, account_id: str, as_of: datetime | None = None) -> PortfolioValuation:
        account = self.get_account(account_id)
        transactions = self._filter_transactions_as_of(account.transactions, as_of)
        cash_balance = self._calculate_cash_balance_from_transactions(transactions)
        holdings = self._calculate_holdings_from_transactions(transactions)
        positions: list[PositionValuation] = []
        securities_value = Decimal("0")
        for symbol in sorted(sym for sym, qty in holdings.items() if qty > 0):
            quantity = holdings[symbol]
            price = self._price_service.get_price(symbol, as_of)
            market_value = quantity * price
            securities_value += market_value
            positions.append(PositionValuation(symbol=symbol, quantity=quantity, price=price, market_value=market_value))
        total_value = cash_balance + securities_value
        net_external = self._calculate_net_external_contributions_from_transactions(transactions)
        profit_loss = total_value - net_external
        return PortfolioValuation(account_id=account_id, as_of=as_of, cash_balance=cash_balance, positions=positions, securities_value=securities_value, total_value=total_value, net_external_contributions=net_external, profit_loss=profit_loss)

    def get_profit_loss(self, account_id: str, as_of: datetime | None = None) -> Decimal:
        return self.get_portfolio_valuation(account_id, as_of).profit_loss

    def get_net_external_contributions(self, account_id: str, as_of: datetime | None = None) -> Decimal:
        account = self.get_account(account_id)
        transactions = self._filter_transactions_as_of(account.transactions, as_of)
        return self._calculate_net_external_contributions_from_transactions(transactions)

    def list_transactions(self, account_id: str, start_time: datetime | None = None, end_time: datetime | None = None) -> list[Transaction]:
        account = self.get_account(account_id)
        txs = self._sort_transactions(account.transactions)
        result = []
        start = self._to_utc(start_time) if start_time is not None else None
        end = self._to_utc(end_time) if end_time is not None else None
        for tx in txs:
            if start is not None and tx.timestamp < start:
                continue
            if end is not None and tx.timestamp > end:
                continue
            result.append(tx)
        return result

    def _create_transaction(self, account: Account, transaction_type: str, timestamp: datetime, cash_delta: Decimal, symbol: str | None, quantity: Decimal | None, execution_price: Decimal | None, notes: str | None) -> Transaction:
        tx = Transaction(str(uuid4()), account.account_id, account.next_sequence, transaction_type, self._to_utc(timestamp), cash_delta, symbol, quantity, execution_price, notes)
        account.transactions.append(tx)
        account.next_sequence += 1
        self._repository.save_account(account)
        return tx

    def _get_effective_timestamp(self, timestamp: datetime | None) -> datetime:
        return self._to_utc(timestamp or datetime.now(timezone.utc))

    def _validate_account_owner_name(self, owner_name: str) -> None:
        if owner_name is None or not str(owner_name).strip():
            raise ValidationError("owner_name is required")

    def _validate_positive_amount(self, amount: Decimal, field_name: str) -> None:
        if amount is None or amount <= 0:
            raise ValidationError(f"{field_name} must be greater than zero")

    def _validate_non_negative_amount(self, amount: Decimal, field_name: str) -> None:
        if amount is None or amount < 0:
            raise ValidationError(f"{field_name} must be greater than or equal to zero")

    def _validate_positive_quantity(self, quantity: Decimal) -> None:
        if quantity is None or quantity <= 0:
            raise ValidationError("quantity must be greater than zero")

    def _normalize_symbol(self, symbol: str) -> str:
        if symbol is None or not str(symbol).strip():
            raise ValidationError("symbol is required")
        return str(symbol).strip().upper()

    def _filter_transactions_as_of(self, transactions: list[Transaction], as_of: datetime | None) -> list[Transaction]:
        if as_of is None:
            return self._sort_transactions(transactions)
        cutoff = self._to_utc(as_of)
        return [tx for tx in self._sort_transactions(transactions) if tx.timestamp <= cutoff]

    def _sort_transactions(self, transactions: list[Transaction]) -> list[Transaction]:
        return sorted(transactions, key=lambda tx: tx.sequence)

    def _calculate_cash_balance_from_transactions(self, transactions: list[Transaction]) -> Decimal:
        balance = Decimal("0")
        for tx in transactions:
            balance += tx.cash_delta
        return balance

    def _calculate_holdings_from_transactions(self, transactions: list[Transaction]) -> dict[str, Decimal]:
        holdings: dict[str, Decimal] = defaultdict(lambda: Decimal("0"))
        for tx in transactions:
            if tx.transaction_type == TRANSACTION_TYPE_BUY:
                holdings[tx.symbol or ""] += tx.quantity or Decimal("0")
            elif tx.transaction_type == TRANSACTION_TYPE_SELL:
                holdings[tx.symbol or ""] -= tx.quantity or Decimal("0")
        return dict(holdings)

    def _calculate_net_external_contributions_from_transactions(self, transactions: list[Transaction]) -> Decimal:
        deposits = Decimal("0")
        withdrawals = Decimal("0")
        for tx in transactions:
            if tx.transaction_type == TRANSACTION_TYPE_DEPOSIT:
                deposits += tx.cash_delta
            elif tx.transaction_type == TRANSACTION_TYPE_WITHDRAWAL:
                withdrawals += -tx.cash_delta
        return deposits - withdrawals

    def _to_utc(self, value: datetime) -> datetime:
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc)
