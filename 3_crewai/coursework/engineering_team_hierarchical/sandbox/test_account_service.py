from __future__ import annotations

import unittest
from datetime import datetime, timezone
from decimal import Decimal

from account_service import AccountService
from exceptions import (
    AccountNotFoundError,
    InsufficientFundsError,
    InsufficientHoldingsError,
    UnknownSymbolError,
    ValidationError,
)
from models import (
    TRANSACTION_TYPE_BUY,
    TRANSACTION_TYPE_DEPOSIT,
    TRANSACTION_TYPE_SELL,
    TRANSACTION_TYPE_WITHDRAWAL,
)
from price_service import PriceService
from repository import InMemoryAccountRepository


class AccountServiceTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.repo = InMemoryAccountRepository()
        self.price_service = PriceService()
        self.service = AccountService(self.repo, self.price_service)
        self.ts1 = datetime(2024, 1, 1, 10, 0, tzinfo=timezone.utc)
        self.ts2 = datetime(2024, 1, 1, 11, 0, tzinfo=timezone.utc)
        self.ts3 = datetime(2024, 1, 1, 12, 0, tzinfo=timezone.utc)
        self.ts4 = datetime(2024, 1, 1, 13, 0, tzinfo=timezone.utc)

    def _create_account(self, initial_deposit: Decimal = Decimal("1000")):
        return self.service.create_account("Alice", initial_deposit, timestamp=self.ts1)


class AccountCreationTests(AccountServiceTestCase):
    def test_create_account_with_initial_deposit(self) -> None:
        account = self._create_account()
        self.assertEqual(account.owner_name, "Alice")
        self.assertEqual(account.created_at, self.ts1)
        self.assertEqual(account.initial_deposit, Decimal("1000"))
        self.assertEqual(len(account.transactions), 1)
        self.assertEqual(account.transactions[0].transaction_type, TRANSACTION_TYPE_DEPOSIT)
        self.assertEqual(account.transactions[0].cash_delta, Decimal("1000"))

    def test_create_account_with_zero_initial_deposit(self) -> None:
        account = self._create_account(Decimal("0"))
        self.assertEqual(account.initial_deposit, Decimal("0"))
        self.assertEqual(account.transactions, [])

    def test_create_account_rejects_negative_initial_deposit(self) -> None:
        with self.assertRaises(ValidationError):
            self.service.create_account("Alice", Decimal("-1"), timestamp=self.ts1)

    def test_create_account_rejects_blank_owner_name(self) -> None:
        with self.assertRaises(ValidationError):
            self.service.create_account("   ", Decimal("1"), timestamp=self.ts1)

    def test_list_accounts_returns_created_accounts(self) -> None:
        a1 = self._create_account()
        a2 = self.service.create_account("Bob", Decimal("0"), timestamp=self.ts2)
        accounts = self.service.list_accounts()
        self.assertEqual([a.account_id for a in accounts], [a1.account_id, a2.account_id])


class DepositTests(AccountServiceTestCase):
    def setUp(self) -> None:
        super().setUp()
        self.account = self._create_account()

    def test_deposit_increases_cash_balance(self) -> None:
        self.service.deposit(self.account.account_id, Decimal("250"), timestamp=self.ts2)
        self.assertEqual(self.service.get_cash_balance(self.account.account_id), Decimal("1250"))

    def test_deposit_records_transaction(self) -> None:
        tx = self.service.deposit(self.account.account_id, Decimal("250"), timestamp=self.ts2, notes="bonus")
        self.assertEqual(tx.transaction_type, TRANSACTION_TYPE_DEPOSIT)
        self.assertEqual(tx.sequence, 2)
        self.assertEqual(tx.cash_delta, Decimal("250"))
        self.assertEqual(tx.notes, "bonus")

    def test_deposit_rejects_zero_amount(self) -> None:
        with self.assertRaises(ValidationError):
            self.service.deposit(self.account.account_id, Decimal("0"), timestamp=self.ts2)

    def test_deposit_rejects_negative_amount(self) -> None:
        with self.assertRaises(ValidationError):
            self.service.deposit(self.account.account_id, Decimal("-1"), timestamp=self.ts2)

    def test_deposit_unknown_account_raises(self) -> None:
        with self.assertRaises(AccountNotFoundError):
            self.service.deposit("missing", Decimal("1"), timestamp=self.ts2)


class WithdrawalTests(AccountServiceTestCase):
    def setUp(self) -> None:
        super().setUp()
        self.account = self._create_account()

    def test_withdraw_decreases_cash_balance(self) -> None:
        self.service.withdraw(self.account.account_id, Decimal("250"), timestamp=self.ts2)
        self.assertEqual(self.service.get_cash_balance(self.account.account_id), Decimal("750"))

    def test_withdraw_records_transaction(self) -> None:
        tx = self.service.withdraw(self.account.account_id, Decimal("250"), timestamp=self.ts2, notes="rent")
        self.assertEqual(tx.transaction_type, TRANSACTION_TYPE_WITHDRAWAL)
        self.assertEqual(tx.sequence, 2)
        self.assertEqual(tx.cash_delta, Decimal("-250"))
        self.assertEqual(tx.notes, "rent")

    def test_withdraw_rejects_zero_amount(self) -> None:
        with self.assertRaises(ValidationError):
            self.service.withdraw(self.account.account_id, Decimal("0"), timestamp=self.ts2)

    def test_withdraw_rejects_negative_amount(self) -> None:
        with self.assertRaises(ValidationError):
            self.service.withdraw(self.account.account_id, Decimal("-1"), timestamp=self.ts2)

    def test_withdraw_rejects_insufficient_funds(self) -> None:
        with self.assertRaises(InsufficientFundsError):
            self.service.withdraw(self.account.account_id, Decimal("1001"), timestamp=self.ts2)

    def test_failed_withdraw_does_not_record_transaction(self) -> None:
        before = len(self.account.transactions)
        with self.assertRaises(InsufficientFundsError):
            self.service.withdraw(self.account.account_id, Decimal("1001"), timestamp=self.ts2)
        self.assertEqual(len(self.account.transactions), before)


class BuyTests(AccountServiceTestCase):
    def setUp(self) -> None:
        super().setUp()
        self.account = self._create_account()

    def test_buy_decreases_cash_and_increases_holdings(self) -> None:
        self.service.buy_shares(self.account.account_id, "aapl", Decimal("2"), timestamp=self.ts2)
        self.assertEqual(self.service.get_cash_balance(self.account.account_id), Decimal("700"))
        holdings = self.service.get_holdings(self.account.account_id)
        self.assertEqual(holdings[0].symbol, "AAPL")
        self.assertEqual(holdings[0].quantity, Decimal("2"))

    def test_buy_records_execution_price(self) -> None:
        tx = self.service.buy_shares(self.account.account_id, "AAPL", Decimal("1"), timestamp=self.ts2)
        self.assertEqual(tx.execution_price, Decimal("150"))
        self.assertEqual(tx.cash_delta, Decimal("-150"))

    def test_buy_records_transaction(self) -> None:
        tx = self.service.buy_shares(self.account.account_id, "AAPL", Decimal("1"), timestamp=self.ts2, notes="trade")
        self.assertEqual(tx.transaction_type, TRANSACTION_TYPE_BUY)
        self.assertEqual(tx.symbol, "AAPL")
        self.assertEqual(tx.quantity, Decimal("1"))
        self.assertEqual(tx.notes, "trade")

    def test_buy_rejects_insufficient_funds(self) -> None:
        with self.assertRaises(InsufficientFundsError):
            self.service.buy_shares(self.account.account_id, "GOOGL", Decimal("1"), timestamp=self.ts2)

    def test_failed_buy_does_not_record_transaction(self) -> None:
        before = len(self.account.transactions)
        with self.assertRaises(InsufficientFundsError):
            self.service.buy_shares(self.account.account_id, "GOOGL", Decimal("1"), timestamp=self.ts2)
        self.assertEqual(len(self.account.transactions), before)

    def test_buy_rejects_zero_quantity(self) -> None:
        with self.assertRaises(ValidationError):
            self.service.buy_shares(self.account.account_id, "AAPL", Decimal("0"), timestamp=self.ts2)

    def test_buy_rejects_negative_quantity(self) -> None:
        with self.assertRaises(ValidationError):
            self.service.buy_shares(self.account.account_id, "AAPL", Decimal("-1"), timestamp=self.ts2)

    def test_buy_rejects_unknown_symbol(self) -> None:
        with self.assertRaises(UnknownSymbolError):
            self.service.buy_shares(self.account.account_id, "MSFT", Decimal("1"), timestamp=self.ts2)


class SellTests(AccountServiceTestCase):
    def setUp(self) -> None:
        super().setUp()
        self.account = self._create_account()
        self.service.buy_shares(self.account.account_id, "AAPL", Decimal("2"), timestamp=self.ts2)

    def test_sell_increases_cash_and_decreases_holdings(self) -> None:
        self.service.sell_shares(self.account.account_id, "AAPL", Decimal("1"), timestamp=self.ts3)
        self.assertEqual(self.service.get_cash_balance(self.account.account_id), Decimal("850"))
        holdings = self.service.get_holdings(self.account.account_id)
        self.assertEqual(holdings[0].symbol, "AAPL")
        self.assertEqual(holdings[0].quantity, Decimal("1"))

    def test_sell_records_execution_price(self) -> None:
        tx = self.service.sell_shares(self.account.account_id, "AAPL", Decimal("1"), timestamp=self.ts3)
        self.assertEqual(tx.execution_price, Decimal("150"))
        self.assertEqual(tx.cash_delta, Decimal("150"))

    def test_sell_records_transaction(self) -> None:
        tx = self.service.sell_shares(self.account.account_id, "AAPL", Decimal("1"), timestamp=self.ts3, notes="exit")
        self.assertEqual(tx.transaction_type, TRANSACTION_TYPE_SELL)
        self.assertEqual(tx.symbol, "AAPL")
        self.assertEqual(tx.quantity, Decimal("1"))
        self.assertEqual(tx.notes, "exit")

    def test_sell_rejects_insufficient_holdings(self) -> None:
        with self.assertRaises(InsufficientHoldingsError):
            self.service.sell_shares(self.account.account_id, "AAPL", Decimal("3"), timestamp=self.ts3)

    def test_failed_sell_does_not_record_transaction(self) -> None:
        before = len(self.account.transactions)
        with self.assertRaises(InsufficientHoldingsError):
            self.service.sell_shares(self.account.account_id, "AAPL", Decimal("3"), timestamp=self.ts3)
        self.assertEqual(len(self.account.transactions), before)

    def test_sell_rejects_zero_quantity(self) -> None:
        with self.assertRaises(ValidationError):
            self.service.sell_shares(self.account.account_id, "AAPL", Decimal("0"), timestamp=self.ts3)

    def test_sell_rejects_negative_quantity(self) -> None:
        with self.assertRaises(ValidationError):
            self.service.sell_shares(self.account.account_id, "AAPL", Decimal("-1"), timestamp=self.ts3)

    def test_sell_rejects_unknown_symbol(self) -> None:
        with self.assertRaises(UnknownSymbolError):
            self.service.sell_shares(self.account.account_id, "MSFT", Decimal("1"), timestamp=self.ts3)
