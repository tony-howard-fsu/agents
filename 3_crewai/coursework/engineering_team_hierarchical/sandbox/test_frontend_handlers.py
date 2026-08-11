from __future__ import annotations

import unittest
from datetime import datetime, timezone
from decimal import Decimal

import app


class FrontendHandlerTests(unittest.TestCase):
    def setUp(self) -> None:
        app._GLOBAL_SERVICE = None
        self.service = app.get_global_service()
        self.t1 = datetime(2024, 1, 1, 10, 0, tzinfo=timezone.utc)
        self.t2 = datetime(2024, 1, 1, 11, 0, tzinfo=timezone.utc)
        self.t3 = datetime(2024, 1, 1, 12, 0, tzinfo=timezone.utc)
        self.account = self.service.create_account("Alice", Decimal("1000"), timestamp=self.t1)

    def test_create_account_handler_success(self) -> None:
        status, update = app.handle_create_account("Bob", 500)
        self.assertIn("**Success:**", status)
        self.assertIn("Created account", status)
        self.assertIsInstance(update, dict)
        self.assertIn("choices", update)

    def test_create_account_handler_validation_error(self) -> None:
        status, update = app.handle_create_account("   ", 500)
        self.assertTrue(status.startswith("**Error:**"))
        self.assertIsInstance(update, dict)

    def test_deposit_handler_requires_account(self) -> None:
        status = app.handle_deposit(None, 100)
        self.assertTrue(status.startswith("**Error:**"))
        self.assertIn("Please select an account", status)

    def test_withdraw_handler_returns_error_for_insufficient_funds(self) -> None:
        status = app.handle_withdraw(self.account.account_id, 100000)
        self.assertTrue(status.startswith("**Error:**"))
        self.assertIn("Insufficient cash", status)

    def test_buy_handler_returns_error_for_insufficient_funds(self) -> None:
        status = app.handle_buy(self.account.account_id, "GOOGL", 1)
        self.assertTrue(status.startswith("**Error:**"))
        self.assertIn("Insufficient cash", status)

    def test_sell_handler_returns_error_for_insufficient_holdings(self) -> None:
        status = app.handle_sell(self.account.account_id, "AAPL", 1)
        self.assertTrue(status.startswith("**Error:**"))
        self.assertIn("Insufficient holdings", status)

    def test_show_holdings_handler_returns_table_rows(self) -> None:
        self.service.buy_shares(self.account.account_id, "AAPL", Decimal("2"), timestamp=self.t2)
        status, rows = app.handle_show_holdings(self.account.account_id, None)
        self.assertIn("Holdings for", status)
        self.assertEqual(rows, [["AAPL", "2"]])

    def test_show_transactions_handler_returns_table_rows(self) -> None:
        self.service.deposit(self.account.account_id, Decimal("100"), timestamp=self.t2)
        status, rows = app.handle_show_transactions(self.account.account_id, None, None)
        self.assertIn("Transactions for", status)
        self.assertGreaterEqual(len(rows), 2)

    def test_show_valuation_handler_returns_summary_markdown(self) -> None:
        self.service.buy_shares(self.account.account_id, "AAPL", Decimal("2"), timestamp=self.t2)
        status, rows, summary = app.handle_show_valuation(self.account.account_id, None)
        self.assertIn("Valuation for", status)
        self.assertEqual(rows, [["AAPL", "2", "$150.00", "$300.00"]])
        self.assertIn("Total Portfolio Value", summary)
        self.assertIn("Profit / Loss", summary)
