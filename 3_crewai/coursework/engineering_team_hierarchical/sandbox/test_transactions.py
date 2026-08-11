from __future__ import annotations

import unittest
from datetime import datetime, timezone
from decimal import Decimal

from account_service import AccountService
from exceptions import InsufficientFundsError, InsufficientHoldingsError
from price_service import PriceService
from repository import InMemoryAccountRepository


class TransactionListingTests(unittest.TestCase):
    def setUp(self) -> None:
        self.repo = InMemoryAccountRepository()
        self.service = AccountService(self.repo, PriceService())
        self.t1 = datetime(2024, 1, 1, 10, 0, tzinfo=timezone.utc)
        self.t2 = datetime(2024, 1, 1, 11, 0, tzinfo=timezone.utc)
        self.t3 = datetime(2024, 1, 1, 12, 0, tzinfo=timezone.utc)
        self.t4 = datetime(2024, 1, 1, 13, 0, tzinfo=timezone.utc)
        self.account = self.service.create_account("Alice", Decimal("1000"), timestamp=self.t1)
        self.tx2 = self.service.deposit(self.account.account_id, Decimal("250"), timestamp=self.t2)
        self.tx3 = self.service.buy_shares(self.account.account_id, "AAPL", Decimal("2"), timestamp=self.t3)
        self.tx4 = self.service.sell_shares(self.account.account_id, "AAPL", Decimal("1"), timestamp=self.t4)

    def test_list_transactions_returns_all_in_sequence_order(self) -> None:
        txs = self.service.list_transactions(self.account.account_id)
        self.assertEqual([tx.sequence for tx in txs], [1, 2, 3, 4])

    def test_list_transactions_filters_start_time(self) -> None:
        txs = self.service.list_transactions(self.account.account_id, start_time=self.t3)
        self.assertEqual([tx.sequence for tx in txs], [3, 4])

    def test_list_transactions_filters_end_time(self) -> None:
        txs = self.service.list_transactions(self.account.account_id, end_time=self.t2)
        self.assertEqual([tx.sequence for tx in txs], [1, 2])

    def test_list_transactions_filters_start_and_end_time(self) -> None:
        txs = self.service.list_transactions(self.account.account_id, start_time=self.t2, end_time=self.t3)
        self.assertEqual([tx.sequence for tx in txs], [2, 3])

    def test_transaction_sequence_numbers_are_monotonic(self) -> None:
        txs = self.service.list_transactions(self.account.account_id)
        self.assertEqual([tx.sequence for tx in txs], sorted(tx.sequence for tx in txs))
        self.assertEqual(txs[0].sequence, 1)
        self.assertEqual(txs[-1].sequence, 4)

    def test_transaction_ids_are_unique(self) -> None:
        txs = self.service.list_transactions(self.account.account_id)
        self.assertEqual(len({tx.transaction_id for tx in txs}), len(txs))

    def test_failed_operations_do_not_create_transactions(self) -> None:
        before = len(self.service.list_transactions(self.account.account_id))
        with self.assertRaises(InsufficientFundsError):
            self.service.withdraw(self.account.account_id, Decimal("100000"), timestamp=self.t4)
        with self.assertRaises(InsufficientHoldingsError):
            self.service.sell_shares(self.account.account_id, "AAPL", Decimal("10"), timestamp=self.t4)
        after = len(self.service.list_transactions(self.account.account_id))
        self.assertEqual(before, after)
