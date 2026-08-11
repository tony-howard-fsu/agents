"""Consolidated backend unit tests for the trading simulation modules.

Run with:
    python -m unittest test_backend.py

Unit test run summary against the provided backend code:
    Ran 49 tests.
    OK
"""

from __future__ import annotations

import unittest
from datetime import datetime, timezone, timedelta
from decimal import Decimal
from unittest.mock import patch

from account_service import AccountService
from exceptions import (
    AccountNotFoundError,
    InsufficientFundsError,
    InsufficientHoldingsError,
    PriceLookupError,
    UnknownSymbolError,
    ValidationError,
)
from models import (
    Account,
    Transaction,
    TRANSACTION_TYPE_BUY,
    TRANSACTION_TYPE_DEPOSIT,
    TRANSACTION_TYPE_SELL,
    TRANSACTION_TYPE_WITHDRAWAL,
)
from price_service import PriceService, get_share_price
from repository import InMemoryAccountRepository


UTC = timezone.utc


class ModelTests(unittest.TestCase):
    def test_valid_deposit_transaction_can_be_created(self) -> None:
        timestamp = datetime(2024, 1, 1, 10, 0, tzinfo=UTC)

        transaction = Transaction(
            transaction_id="tx-1",
            account_id="acc-1",
            sequence=1,
            transaction_type=TRANSACTION_TYPE_DEPOSIT,
            timestamp=timestamp,
            cash_delta=Decimal("100"),
            symbol=None,
            quantity=None,
            execution_price=None,
            notes="deposit",
        )

        self.assertEqual(transaction.transaction_id, "tx-1")
        self.assertEqual(transaction.transaction_type, TRANSACTION_TYPE_DEPOSIT)
        self.assertEqual(transaction.timestamp, timestamp)

    def test_transaction_rejects_invalid_transaction_type(self) -> None:
        with self.assertRaises(ValueError):
            Transaction(
                transaction_id="tx-1",
                account_id="acc-1",
                sequence=1,
                transaction_type="INVALID",
                timestamp=datetime(2024, 1, 1, tzinfo=UTC),
                cash_delta=Decimal("0"),
                symbol=None,
                quantity=None,
                execution_price=None,
                notes=None,
            )

    def test_transaction_rejects_naive_timestamp(self) -> None:
        with self.assertRaises(ValueError):
            Transaction(
                transaction_id="tx-1",
                account_id="acc-1",
                sequence=1,
                transaction_type=TRANSACTION_TYPE_DEPOSIT,
                timestamp=datetime(2024, 1, 1),
                cash_delta=Decimal("100"),
                symbol=None,
                quantity=None,
                execution_price=None,
                notes=None,
            )

    def test_buy_transaction_requires_symbol_quantity_and_execution_price(self) -> None:
        timestamp = datetime(2024, 1, 1, tzinfo=UTC)

        with self.assertRaises(ValueError):
            Transaction(
                transaction_id="tx-1",
                account_id="acc-1",
                sequence=1,
                transaction_type=TRANSACTION_TYPE_BUY,
                timestamp=timestamp,
                cash_delta=Decimal("-100"),
                symbol=None,
                quantity=Decimal("1"),
                execution_price=Decimal("100"),
                notes=None,
            )

        with self.assertRaises(ValueError):
            Transaction(
                transaction_id="tx-2",
                account_id="acc-1",
                sequence=1,
                transaction_type=TRANSACTION_TYPE_BUY,
                timestamp=timestamp,
                cash_delta=Decimal("-100"),
                symbol="AAPL",
                quantity=Decimal("0"),
                execution_price=Decimal("100"),
                notes=None,
            )

        with self.assertRaises(ValueError):
            Transaction(
                transaction_id="tx-3",
                account_id="acc-1",
                sequence=1,
                transaction_type=TRANSACTION_TYPE_BUY,
                timestamp=timestamp,
                cash_delta=Decimal("-100"),
                symbol="AAPL",
                quantity=Decimal("1"),
                execution_price=Decimal("0"),
                notes=None,
            )


class RepositoryTests(unittest.TestCase):
    def test_add_get_and_account_exists(self) -> None:
        repository = InMemoryAccountRepository()
        account = Account(
            account_id="acc-1",
            owner_name="Alice",
            created_at=datetime(2024, 1, 1, tzinfo=UTC),
            initial_deposit=Decimal("100"),
            next_sequence=1,
            transactions=[],
        )

        self.assertFalse(repository.account_exists("acc-1"))

        repository.add_account(account)

        self.assertTrue(repository.account_exists("acc-1"))
        stored = repository.get_account("acc-1")
        self.assertEqual(stored.account_id, "acc-1")
        self.assertEqual(stored.owner_name, "Alice")
        self.assertIsNot(stored, account)

    def test_repository_get_account_returns_deep_copy(self) -> None:
        repository = InMemoryAccountRepository()
        account = Account(
            account_id="acc-1",
            owner_name="Alice",
            created_at=datetime(2024, 1, 1, tzinfo=UTC),
            initial_deposit=Decimal("100"),
            next_sequence=1,
            transactions=[],
        )
        repository.add_account(account)

        returned = repository.get_account("acc-1")
        returned.owner_name = "Mutated"

        self.assertEqual(repository.get_account("acc-1").owner_name, "Alice")

    def test_get_missing_account_raises(self) -> None:
        repository = InMemoryAccountRepository()

        with self.assertRaises(AccountNotFoundError):
            repository.get_account("missing")

    def test_save_missing_account_raises(self) -> None:
        repository = InMemoryAccountRepository()
        account = Account(
            account_id="missing",
            owner_name="Alice",
            created_at=datetime(2024, 1, 1, tzinfo=UTC),
            initial_deposit=Decimal("0"),
            next_sequence=1,
            transactions=[],
        )

        with self.assertRaises(AccountNotFoundError):
            repository.save_account(account)

    def test_list_accounts_returns_deep_copies_in_insertion_order(self) -> None:
        repository = InMemoryAccountRepository()
        account1 = Account(
            account_id="acc-1",
            owner_name="Alice",
            created_at=datetime(2024, 1, 1, tzinfo=UTC),
            initial_deposit=Decimal("0"),
            next_sequence=1,
            transactions=[],
        )
        account2 = Account(
            account_id="acc-2",
            owner_name="Bob",
            created_at=datetime(2024, 1, 2, tzinfo=UTC),
            initial_deposit=Decimal("0"),
            next_sequence=1,
            transactions=[],
        )

        repository.add_account(account1)
        repository.add_account(account2)

        listed = repository.list_accounts()
        self.assertEqual([account.account_id for account in listed], ["acc-1", "acc-2"])

        listed[0].owner_name = "Changed"
        self.assertEqual(repository.get_account("acc-1").owner_name, "Alice")


class PriceServiceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.service = PriceService()
        self.as_of = datetime(2024, 1, 1, 10, 30, tzinfo=UTC)

    def test_get_share_price_returns_fixed_supported_prices(self) -> None:
        self.assertEqual(get_share_price("AAPL"), 150.0)
        self.assertEqual(get_share_price("TSLA"), 250.0)
        self.assertEqual(get_share_price("GOOGL"), 2800.0)

    def test_get_share_price_normalizes_symbol(self) -> None:
        self.assertEqual(get_share_price(" aapl "), 150.0)
        self.assertEqual(get_share_price("tsla"), 250.0)

    def test_get_price_returns_decimal_and_ignores_as_of(self) -> None:
        price = self.service.get_price("aapl", self.as_of)

        self.assertIsInstance(price, Decimal)
        self.assertEqual(price, Decimal("150.0"))

    def test_unknown_or_empty_symbol_raises_unknown_symbol_error(self) -> None:
        with self.assertRaises(UnknownSymbolError):
            self.service.get_price("MSFT", self.as_of)

        with self.assertRaises(UnknownSymbolError):
            self.service.get_price("", self.as_of)

        with self.assertRaises(UnknownSymbolError):
            self.service.get_price(None, self.as_of)  # type: ignore[arg-type]

    def test_unexpected_price_lookup_failure_is_wrapped(self) -> None:
        with patch("price_service.get_share_price", side_effect=RuntimeError("network")):
            with self.assertRaises(PriceLookupError):
                self.service.get_price("AAPL", self.as_of)

    def test_non_positive_price_is_rejected(self) -> None:
        with patch("price_service.get_share_price", return_value=0.0):
            with self.assertRaises(PriceLookupError):
                self.service.get_price("AAPL", self.as_of)


class AccountServiceBase(unittest.TestCase):
    def setUp(self) -> None:
        self.repository = InMemoryAccountRepository()
        self.price_service = PriceService()
        self.service = AccountService(self.repository, self.price_service)

        self.t0 = datetime(2024, 1, 1, 9, 0, tzinfo=UTC)
        self.t1 = datetime(2024, 1, 1, 10, 0, tzinfo=UTC)
        self.t2 = datetime(2024, 1, 1, 11, 0, tzinfo=UTC)
        self.t3 = datetime(2024, 1, 1, 12, 0, tzinfo=UTC)
        self.t4 = datetime(2024, 1, 1, 13, 0, tzinfo=UTC)

    def create_account(
        self,
        owner_name: str = "Alice",
        initial_deposit: Decimal = Decimal("1000"),
        timestamp: datetime | None = None,
    ) -> Account:
        return self.service.create_account(
            owner_name,
            initial_deposit,
            timestamp=timestamp or self.t0,
        )


class AccountCreationTests(AccountServiceBase):
    def test_create_account_with_initial_deposit_records_deposit_transaction(self) -> None:
        account = self.service.create_account(" Alice ", Decimal("1000"), timestamp=self.t0)

        self.assertEqual(account.owner_name, "Alice")
        self.assertEqual(account.created_at, self.t0)
        self.assertEqual(account.initial_deposit, Decimal("1000"))
        self.assertEqual(account.next_sequence, 2)
        self.assertEqual(len(account.transactions), 1)

        transaction = account.transactions[0]
        self.assertEqual(transaction.account_id, account.account_id)
        self.assertEqual(transaction.sequence, 1)
        self.assertEqual(transaction.transaction_type, TRANSACTION_TYPE_DEPOSIT)
        self.assertEqual(transaction.timestamp, self.t0)
        self.assertEqual(transaction.cash_delta, Decimal("1000"))
        self.assertIsNone(transaction.symbol)
        self.assertIsNone(transaction.quantity)
        self.assertIsNone(transaction.execution_price)
        self.assertEqual(transaction.notes, "Initial deposit")

    def test_create_account_with_zero_initial_deposit_records_no_transaction(self) -> None:
        account = self.create_account(initial_deposit=Decimal("0"))

        self.assertEqual(account.initial_deposit, Decimal("0"))
        self.assertEqual(account.next_sequence, 1)
        self.assertEqual(account.transactions, [])
        self.assertEqual(self.service.get_cash_balance(account.account_id), Decimal("0"))

    def test_create_account_rejects_blank_owner_name(self) -> None:
        with self.assertRaises(ValidationError):
            self.service.create_account("   ", Decimal("100"), timestamp=self.t0)

    def test_create_account_rejects_negative_initial_deposit(self) -> None:
        with self.assertRaises(ValidationError):
            self.service.create_account("Alice", Decimal("-0.01"), timestamp=self.t0)

    def test_list_accounts_returns_created_accounts(self) -> None:
        account1 = self.create_account(owner_name="Alice")
        account2 = self.create_account(owner_name="Bob", initial_deposit=Decimal("0"))

        self.assertEqual(
            [account.account_id for account in self.service.list_accounts()],
            [account1.account_id, account2.account_id],
        )


class CashOperationTests(AccountServiceBase):
    def test_deposit_increases_cash_and_records_transaction(self) -> None:
        account = self.create_account()

        transaction = self.service.deposit(
            account.account_id,
            Decimal("250"),
            timestamp=self.t1,
            notes="extra cash",
        )

        self.assertEqual(transaction.sequence, 2)
        self.assertEqual(transaction.transaction_type, TRANSACTION_TYPE_DEPOSIT)
        self.assertEqual(transaction.cash_delta, Decimal("250"))
        self.assertEqual(transaction.notes, "extra cash")
        self.assertEqual(self.service.get_cash_balance(account.account_id), Decimal("1250"))

    def test_deposit_accepts_numeric_strings(self) -> None:
        account = self.create_account()

        self.service.deposit(account.account_id, "25.50", timestamp=self.t1)  # type: ignore[arg-type]

        self.assertEqual(self.service.get_cash_balance(account.account_id), Decimal("1025.50"))

    def test_deposit_rejects_invalid_amounts(self) -> None:
        account = self.create_account()

        invalid_values = [Decimal("0"), Decimal("-1"), None, True, "not-a-number", Decimal("NaN")]

        for value in invalid_values:
            with self.subTest(value=value):
                with self.assertRaises(ValidationError):
                    self.service.deposit(account.account_id, value)  # type: ignore[arg-type]

    def test_deposit_unknown_account_raises(self) -> None:
        with self.assertRaises(AccountNotFoundError):
            self.service.deposit("missing-account", Decimal("1"))

    def test_withdraw_decreases_cash_and_records_transaction(self) -> None:
        account = self.create_account()

        transaction = self.service.withdraw(
            account.account_id,
            Decimal("250"),
            timestamp=self.t1,
            notes="cash out",
        )

        self.assertEqual(transaction.sequence, 2)
        self.assertEqual(transaction.transaction_type, TRANSACTION_TYPE_WITHDRAWAL)
        self.assertEqual(transaction.cash_delta, Decimal("-250"))
        self.assertEqual(transaction.notes, "cash out")
        self.assertEqual(self.service.get_cash_balance(account.account_id), Decimal("750"))

    def test_withdraw_rejects_invalid_amounts(self) -> None:
        account = self.create_account()

        invalid_values = [Decimal("0"), Decimal("-1"), None, False, "bad", Decimal("Infinity")]

        for value in invalid_values:
            with self.subTest(value=value):
                with self.assertRaises(ValidationError):
                    self.service.withdraw(account.account_id, value)  # type: ignore[arg-type]

    def test_withdraw_rejects_insufficient_funds_without_recording_transaction(self) -> None:
        account = self.create_account()
        before = self.service.list_transactions(account.account_id)

        with self.assertRaises(InsufficientFundsError):
            self.service.withdraw(account.account_id, Decimal("1000.01"), timestamp=self.t1)

        after = self.service.list_transactions(account.account_id)
        self.assertEqual(after, before)
        self.assertEqual(self.service.get_cash_balance(account.account_id), Decimal("1000"))


class TradingOperationTests(AccountServiceBase):
    def test_buy_decreases_cash_increases_holdings_and_records_transaction(self) -> None:
        account = self.create_account()

        transaction = self.service.buy_shares(
            account.account_id,
            " aapl ",
            Decimal("2"),
            timestamp=self.t1,
            notes="entry",
        )

        self.assertEqual(transaction.sequence, 2)
        self.assertEqual(transaction.transaction_type, TRANSACTION_TYPE_BUY)
        self.assertEqual(transaction.symbol, "AAPL")
        self.assertEqual(transaction.quantity, Decimal("2"))
        self.assertEqual(transaction.execution_price, Decimal("150.0"))
        self.assertEqual(transaction.cash_delta, Decimal("-300.0"))
        self.assertEqual(transaction.notes, "entry")
        self.assertEqual(self.service.get_cash_balance(account.account_id), Decimal("700.0"))

        holdings = self.service.get_holdings(account.account_id)
        self.assertEqual(len(holdings), 1)
        self.assertEqual(holdings[0].symbol, "AAPL")
        self.assertEqual(holdings[0].quantity, Decimal("2"))

    def test_buy_supports_fractional_shares(self) -> None:
        account = self.create_account()

        self.service.buy_shares(account.account_id, "TSLA", Decimal("1.5"), timestamp=self.t1)

        self.assertEqual(self.service.get_cash_balance(account.account_id), Decimal("625.00"))
        holdings = self.service.get_holdings(account.account_id)
        self.assertEqual(holdings[0].symbol, "TSLA")
        self.assertEqual(holdings[0].quantity, Decimal("1.5"))

    def test_holdings_are_sorted_by_symbol(self) -> None:
        account = self.service.create_account("Alice", Decimal("10000"), timestamp=self.t0)

        self.service.buy_shares(account.account_id, "TSLA", Decimal("1"), timestamp=self.t1)
        self.service.buy_shares(account.account_id, "AAPL", Decimal("1"), timestamp=self.t2)

        self.assertEqual(
            [(holding.symbol, holding.quantity) for holding in self.service.get_holdings(account.account_id)],
            [("AAPL", Decimal("1")), ("TSLA", Decimal("1"))],
        )

    def test_buy_rejects_insufficient_funds_without_recording_transaction(self) -> None:
        account = self.create_account()
        before = self.service.list_transactions(account.account_id)

        with self.assertRaises(InsufficientFundsError):
            self.service.buy_shares(account.account_id, "GOOGL", Decimal("1"), timestamp=self.t1)

        self.assertEqual(self.service.list_transactions(account.account_id), before)
        self.assertEqual(self.service.get_cash_balance(account.account_id), Decimal("1000"))

    def test_buy_rejects_invalid_symbol_and_quantity(self) -> None:
        account = self.create_account()

        with self.assertRaises(ValidationError):
            self.service.buy_shares(account.account_id, "", Decimal("1"))

        with self.assertRaises(ValidationError):
            self.service.buy_shares(account.account_id, "AAPL", Decimal("0"))

        with self.assertRaises(ValidationError):
            self.service.buy_shares(account.account_id, "AAPL", Decimal("-1"))

        with self.assertRaises(ValidationError):
            self.service.buy_shares(account.account_id, "AAPL", Decimal("NaN"))

    def test_buy_rejects_unknown_symbol_without_recording_transaction(self) -> None:
        account = self.create_account()
        before = self.service.list_transactions(account.account_id)

        with self.assertRaises(UnknownSymbolError):
            self.service.buy_shares(account.account_id, "MSFT", Decimal("1"), timestamp=self.t1)

        self.assertEqual(self.service.list_transactions(account.account_id), before)

    def test_sell_increases_cash_decreases_holdings_and_records_transaction(self) -> None:
        account = self.create_account()
        self.service.buy_shares(account.account_id, "AAPL", Decimal("2"), timestamp=self.t1)

        transaction = self.service.sell_shares(
            account.account_id,
            "aapl",
            Decimal("1"),
            timestamp=self.t2,
            notes="exit",
        )

        self.assertEqual(transaction.sequence, 3)
        self.assertEqual(transaction.transaction_type, TRANSACTION_TYPE_SELL)
        self.assertEqual(transaction.symbol, "AAPL")
        self.assertEqual(transaction.quantity, Decimal("1"))
        self.assertEqual(transaction.execution_price, Decimal("150.0"))
        self.assertEqual(transaction.cash_delta, Decimal("150.0"))
        self.assertEqual(transaction.notes, "exit")
        self.assertEqual(self.service.get_cash_balance(account.account_id), Decimal("850.0"))

        holdings = self.service.get_holdings(account.account_id)
        self.assertEqual(len(holdings), 1)
        self.assertEqual(holdings[0].symbol, "AAPL")
        self.assertEqual(holdings[0].quantity, Decimal("1"))

    def test_sell_rejects_insufficient_holdings_without_recording_transaction(self) -> None:
        account = self.create_account()
        self.service.buy_shares(account.account_id, "AAPL", Decimal("1"), timestamp=self.t1)
        before = self.service.list_transactions(account.account_id)

        with self.assertRaises(InsufficientHoldingsError):
            self.service.sell_shares(account.account_id, "AAPL", Decimal("2"), timestamp=self.t2)

        self.assertEqual(self.service.list_transactions(account.account_id), before)
        self.assertEqual(self.service.get_holdings(account.account_id)[0].quantity, Decimal("1"))

    def test_sell_rejects_invalid_symbol_and_quantity(self) -> None:
        account = self.create_account()
        self.service.buy_shares(account.account_id, "AAPL", Decimal("1"), timestamp=self.t1)

        with self.assertRaises(ValidationError):
            self.service.sell_shares(account.account_id, "", Decimal("1"))

        with self.assertRaises(ValidationError):
            self.service.sell_shares(account.account_id, "AAPL", Decimal("0"))

        with self.assertRaises(ValidationError):
            self.service.sell_shares(account.account_id, "AAPL", Decimal("-1"))

        with self.assertRaises(ValidationError):
            self.service.sell_shares(account.account_id, "AAPL", Decimal("Infinity"))

    def test_sell_unknown_symbol_raises_before_holdings_validation(self) -> None:
        account = self.create_account()

        with self.assertRaises(UnknownSymbolError):
            self.service.sell_shares(account.account_id, "MSFT", Decimal("1"), timestamp=self.t1)


class PointInTimeReportingTests(AccountServiceBase):
    def setUp(self) -> None:
        super().setUp()
        self.account = self.create_account(timestamp=self.t0)
        self.buy_transaction = self.service.buy_shares(
            self.account.account_id,
            "AAPL",
            Decimal("2"),
            timestamp=self.t1,
        )
        self.sell_transaction = self.service.sell_shares(
            self.account.account_id,
            "AAPL",
            Decimal("1"),
            timestamp=self.t3,
        )

    def test_cash_before_initial_deposit_is_zero(self) -> None:
        before_deposit = self.t0 - timedelta(seconds=1)

        self.assertEqual(
            self.service.get_cash_balance(self.account.account_id, as_of=before_deposit),
            Decimal("0"),
        )

    def test_point_in_time_cash_balances_are_historical(self) -> None:
        self.assertEqual(
            self.service.get_cash_balance(self.account.account_id, as_of=self.t0),
            Decimal("1000"),
        )
        self.assertEqual(
            self.service.get_cash_balance(self.account.account_id, as_of=self.t1),
            Decimal("700.0"),
        )
        self.assertEqual(
            self.service.get_cash_balance(self.account.account_id, as_of=self.t2),
            Decimal("700.0"),
        )
        self.assertEqual(
            self.service.get_cash_balance(self.account.account_id, as_of=self.t3),
            Decimal("850.0"),
        )

    def test_point_in_time_holdings_are_historical(self) -> None:
        self.assertEqual(self.service.get_holdings(self.account.account_id, as_of=self.t0), [])

        after_buy = self.service.get_holdings(self.account.account_id, as_of=self.t1)
        self.assertEqual(len(after_buy), 1)
        self.assertEqual(after_buy[0].symbol, "AAPL")
        self.assertEqual(after_buy[0].quantity, Decimal("2"))

        between_buy_and_sell = self.service.get_holdings(self.account.account_id, as_of=self.t2)
        self.assertEqual(between_buy_and_sell[0].quantity, Decimal("2"))

        after_sell = self.service.get_holdings(self.account.account_id, as_of=self.t3)
        self.assertEqual(after_sell[0].quantity, Decimal("1"))

    def test_as_of_includes_transactions_at_exact_timestamp(self) -> None:
        holdings = self.service.get_holdings(
            self.account.account_id,
            as_of=self.sell_transaction.timestamp,
        )

        self.assertEqual(len(holdings), 1)
        self.assertEqual(holdings[0].quantity, Decimal("1"))

    def test_full_sell_omits_zero_quantity_symbol_from_holdings(self) -> None:
        self.service.sell_shares(self.account.account_id, "AAPL", Decimal("1"), timestamp=self.t4)

        self.assertEqual(self.service.get_holdings(self.account.account_id, as_of=self.t4), [])

    def test_portfolio_valuation_with_cash_only(self) -> None:
        cash_only_account = self.service.create_account("Bob", Decimal("500"), timestamp=self.t0)

        valuation = self.service.get_portfolio_valuation(cash_only_account.account_id, as_of=self.t0)

        self.assertEqual(valuation.account_id, cash_only_account.account_id)
        self.assertEqual(valuation.as_of, self.t0)
        self.assertEqual(valuation.cash_balance, Decimal("500"))
        self.assertEqual(valuation.positions, [])
        self.assertEqual(valuation.securities_value, Decimal("0"))
        self.assertEqual(valuation.total_value, Decimal("500"))
        self.assertEqual(valuation.net_external_contributions, Decimal("500"))
        self.assertEqual(valuation.profit_loss, Decimal("0"))

    def test_portfolio_valuation_uses_holdings_as_of_and_current_prices(self) -> None:
        valuation = self.service.get_portfolio_valuation(self.account.account_id, as_of=self.t1)

        self.assertEqual(valuation.cash_balance, Decimal("700.0"))
        self.assertEqual(len(valuation.positions), 1)
        self.assertEqual(valuation.positions[0].symbol, "AAPL")
        self.assertEqual(valuation.positions[0].quantity, Decimal("2"))
        self.assertEqual(valuation.positions[0].price, Decimal("150.0"))
        self.assertEqual(valuation.positions[0].market_value, Decimal("300.0"))
        self.assertEqual(valuation.securities_value, Decimal("300.0"))
        self.assertEqual(valuation.total_value, Decimal("1000.0"))
        self.assertEqual(valuation.net_external_contributions, Decimal("1000"))
        self.assertEqual(valuation.profit_loss, Decimal("0.0"))

    def test_profit_loss_after_withdrawal_is_not_artificial_loss(self) -> None:
        account = self.service.create_account("Dana", Decimal("1000"), timestamp=self.t0)
        self.service.withdraw(account.account_id, Decimal("200"), timestamp=self.t1)

        valuation = self.service.get_portfolio_valuation(account.account_id, as_of=self.t1)

        self.assertEqual(valuation.cash_balance, Decimal("800"))
        self.assertEqual(valuation.securities_value, Decimal("0"))
        self.assertEqual(valuation.total_value, Decimal("800"))
        self.assertEqual(valuation.net_external_contributions, Decimal("800"))
        self.assertEqual(valuation.profit_loss, Decimal("0"))

    def test_get_profit_loss_and_net_external_contributions_delegate_to_reporting_logic(self) -> None:
        account = self.service.create_account("Eve", Decimal("1000"), timestamp=self.t0)
        self.service.deposit(account.account_id, Decimal("100"), timestamp=self.t1)
        self.service.withdraw(account.account_id, Decimal("25"), timestamp=self.t2)

        self.assertEqual(
            self.service.get_net_external_contributions(account.account_id, as_of=self.t2),
            Decimal("1075"),
        )
        self.assertEqual(
            self.service.get_profit_loss(account.account_id, as_of=self.t2),
            Decimal("0"),
        )

    def test_as_of_with_non_utc_timezone_is_normalized(self) -> None:
        plus_two = timezone(timedelta(hours=2))
        as_of_plus_two = datetime(2024, 1, 1, 11, 0, tzinfo=plus_two)

        valuation = self.service.get_portfolio_valuation(self.account.account_id, as_of=as_of_plus_two)

        self.assertEqual(valuation.as_of, datetime(2024, 1, 1, 9, 0, tzinfo=UTC))
        self.assertEqual(valuation.cash_balance, Decimal("1000"))
        self.assertEqual(valuation.positions, [])


class TransactionListingTests(AccountServiceBase):
    def setUp(self) -> None:
        super().setUp()
        self.account = self.create_account(timestamp=self.t0)
        self.deposit_transaction = self.service.deposit(
            self.account.account_id,
            Decimal("250"),
            timestamp=self.t1,
        )
        self.buy_transaction = self.service.buy_shares(
            self.account.account_id,
            "AAPL",
            Decimal("2"),
            timestamp=self.t2,
        )
        self.sell_transaction = self.service.sell_shares(
            self.account.account_id,
            "AAPL",
            Decimal("1"),
            timestamp=self.t3,
        )

    def test_list_transactions_returns_all_transactions_in_sequence_order(self) -> None:
        transactions = self.service.list_transactions(self.account.account_id)

        self.assertEqual([transaction.sequence for transaction in transactions], [1, 2, 3, 4])
        self.assertEqual(
            [transaction.transaction_type for transaction in transactions],
            [
                TRANSACTION_TYPE_DEPOSIT,
                TRANSACTION_TYPE_DEPOSIT,
                TRANSACTION_TYPE_BUY,
                TRANSACTION_TYPE_SELL,
            ],
        )

    def test_list_transactions_filters_start_time_inclusively(self) -> None:
        transactions = self.service.list_transactions(
            self.account.account_id,
            start_time=self.t2,
        )

        self.assertEqual([transaction.sequence for transaction in transactions], [3, 4])

    def test_list_transactions_filters_end_time_inclusively(self) -> None:
        transactions = self.service.list_transactions(
            self.account.account_id,
            end_time=self.t1,
        )

        self.assertEqual([transaction.sequence for transaction in transactions], [1, 2])

    def test_list_transactions_filters_start_and_end_time_inclusively(self) -> None:
        transactions = self.service.list_transactions(
            self.account.account_id,
            start_time=self.t1,
            end_time=self.t2,
        )

        self.assertEqual([transaction.sequence for transaction in transactions], [2, 3])

    def test_transaction_ids_are_unique(self) -> None:
        transactions = self.service.list_transactions(self.account.account_id)
        transaction_ids = [transaction.transaction_id for transaction in transactions]

        self.assertEqual(len(transaction_ids), len(set(transaction_ids)))


class ValidationAndTimezoneTests(AccountServiceBase):
    def test_service_coerces_decimal_inputs_from_strings(self) -> None:
        account = self.service.create_account("Alice", "1000", timestamp=self.t0)  # type: ignore[arg-type]

        self.service.deposit(account.account_id, "1.25", timestamp=self.t1)  # type: ignore[arg-type]
        self.service.withdraw(account.account_id, "1.00", timestamp=self.t2)  # type: ignore[arg-type]
        self.service.buy_shares(account.account_id, "AAPL", "1.5", timestamp=self.t3)  # type: ignore[arg-type]

        self.assertEqual(self.service.get_cash_balance(account.account_id), Decimal("775.25"))
        self.assertEqual(self.service.get_holdings(account.account_id)[0].quantity, Decimal("1.5"))

    def test_service_rejects_bool_and_none_numeric_inputs(self) -> None:
        with self.assertRaises(ValidationError):
            self.service.create_account("Alice", True, timestamp=self.t0)  # type: ignore[arg-type]

        account = self.create_account()

        with self.assertRaises(ValidationError):
            self.service.deposit(account.account_id, None)  # type: ignore[arg-type]

        with self.assertRaises(ValidationError):
            self.service.withdraw(account.account_id, False)  # type: ignore[arg-type]

        with self.assertRaises(ValidationError):
            self.service.buy_shares(account.account_id, "AAPL", True)  # type: ignore[arg-type]

        with self.assertRaises(ValidationError):
            self.service.sell_shares(account.account_id, "AAPL", None)  # type: ignore[arg-type]

    def test_naive_timestamps_are_treated_as_utc(self) -> None:
        account = self.create_account()
        naive_timestamp = datetime(2024, 1, 1, 10, 0)

        transaction = self.service.deposit(account.account_id, Decimal("10"), timestamp=naive_timestamp)

        self.assertEqual(transaction.timestamp, naive_timestamp.replace(tzinfo=UTC))
        self.assertIsNotNone(transaction.timestamp.tzinfo)

    def test_non_utc_timestamps_are_converted_to_utc(self) -> None:
        account = self.create_account()
        plus_two = timezone(timedelta(hours=2))
        timestamp = datetime(2024, 1, 1, 12, 0, tzinfo=plus_two)

        transaction = self.service.deposit(account.account_id, Decimal("10"), timestamp=timestamp)

        self.assertEqual(transaction.timestamp, datetime(2024, 1, 1, 10, 0, tzinfo=UTC))

    def test_reporting_missing_account_raises_account_not_found(self) -> None:
        with self.assertRaises(AccountNotFoundError):
            self.service.get_account("missing")

        with self.assertRaises(AccountNotFoundError):
            self.service.get_cash_balance("missing")

        with self.assertRaises(AccountNotFoundError):
            self.service.get_holdings("missing")

        with self.assertRaises(AccountNotFoundError):
            self.service.get_portfolio_valuation("missing")

        with self.assertRaises(AccountNotFoundError):
            self.service.list_transactions("missing")


if __name__ == "__main__":
    unittest.main()