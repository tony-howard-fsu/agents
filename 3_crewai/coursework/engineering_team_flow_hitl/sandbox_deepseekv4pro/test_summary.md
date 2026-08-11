## Final Answer

The test file has been written and executed. All **70 tests pass** with no backend code changes required. The backend module (`portfolio_manager.py`) and Gradio app (`app.py`) remain unchanged.

---

### Complete Test File: `/home/user/sandbox/test_portfolio_manager.py`

```python
"""
test_portfolio_manager.py — Comprehensive unittest suite for the
portfolio_manager backend module.

Uses only the Python standard-library ``unittest`` framework.
Run with:  python -m unittest test_portfolio_manager.py
"""

from __future__ import annotations

import unittest
from datetime import datetime, timezone
from typing import Optional

from portfolio_manager import (
    Account,
    AccountManager,
    SharePriceProvider,
    TestSharePriceProvider,
    Transaction,
    TransactionType,
    get_default_manager,
    reset_manager,
)


# ======================================================================
# TestAccountCreation
# ======================================================================


class TestAccountCreation(unittest.TestCase):
    """Tests for AccountManager.create_account and related CRUD."""

    def setUp(self) -> None:
        """Create a fresh manager before each test."""
        self.price_provider = TestSharePriceProvider()
        self.manager = AccountManager(price_provider=self.price_provider)

    def test_create_account_succeeds(self) -> None:
        account = self.manager.create_account("Alice", 5000.0)
        self.assertEqual(account.name, "Alice")
        self.assertEqual(account.balance, 5000.0)
        self.assertEqual(account.initial_deposit, 5000.0)

    def test_create_account_records_deposit_transaction(self) -> None:
        account = self.manager.create_account("Bob", 1000.0)
        txns = account.transactions
        self.assertEqual(len(txns), 1)
        self.assertEqual(txns[0].transaction_type, TransactionType.DEPOSIT)
        self.assertEqual(txns[0].amount, 1000.0)

    def test_create_account_zero_deposit(self) -> None:
        account = self.manager.create_account("Zero", 0.0)
        self.assertEqual(account.balance, 0.0)
        self.assertEqual(account.total_deposited, 0.0)
        self.assertEqual(len(account.transactions), 0)

    def test_create_account_negative_deposit_raises(self) -> None:
        with self.assertRaises(ValueError):
            self.manager.create_account("Bad", -100.0)

    def test_create_account_empty_name_raises(self) -> None:
        with self.assertRaises(ValueError):
            self.manager.create_account("", 100.0)
        with self.assertRaises(ValueError):
            self.manager.create_account("   ", 100.0)

    def test_list_accounts(self) -> None:
        self.manager.create_account("A", 100.0)
        self.manager.create_account("B", 200.0)
        accounts = self.manager.list_accounts()
        self.assertEqual(len(accounts), 2)
        names = {a.name for a in accounts}
        self.assertEqual(names, {"A", "B"})

    def test_get_account_by_id(self) -> None:
        created = self.manager.create_account("Test", 500.0)
        fetched = self.manager.get_account(created.account_id)
        self.assertEqual(fetched.account_id, created.account_id)
        self.assertEqual(fetched.name, "Test")

    def test_get_account_invalid_id_raises(self) -> None:
        with self.assertRaises(KeyError):
            self.manager.get_account("nonexistent-id")

    def test_delete_account(self) -> None:
        account = self.manager.create_account("DeleteMe", 100.0)
        self.manager.delete_account(account.account_id)
        with self.assertRaises(KeyError):
            self.manager.get_account(account.account_id)

    def test_delete_account_invalid_id_raises(self) -> None:
        with self.assertRaises(KeyError):
            self.manager.delete_account("nonexistent-id")


# ======================================================================
# TestDeposit
# ======================================================================


class TestDeposit(unittest.TestCase):
    """Tests for AccountManager.deposit."""

    def setUp(self) -> None:
        self.price_provider = TestSharePriceProvider()
        self.manager = AccountManager(price_provider=self.price_provider)
        self.account = self.manager.create_account("Test Account", 10000.0)

    def test_deposit_increases_balance(self) -> None:
        self.manager.deposit(self.account.account_id, 500.0)
        updated = self.manager.get_account(self.account.account_id)
        self.assertEqual(updated.balance, 10500.0)

    def test_deposit_records_transaction(self) -> None:
        txn = self.manager.deposit(self.account.account_id, 250.0)
        self.assertEqual(txn.transaction_type, TransactionType.DEPOSIT)
        self.assertEqual(txn.amount, 250.0)
        self.assertEqual(txn.account_id, self.account.account_id)

    def test_deposit_zero_amount_raises(self) -> None:
        with self.assertRaises(ValueError):
            self.manager.deposit(self.account.account_id, 0.0)

    def test_deposit_negative_amount_raises(self) -> None:
        with self.assertRaises(ValueError):
            self.manager.deposit(self.account.account_id, -50.0)


# ======================================================================
# TestWithdrawal
# ======================================================================


class TestWithdrawal(unittest.TestCase):
    """Tests for AccountManager.withdraw."""

    def setUp(self) -> None:
        self.price_provider = TestSharePriceProvider()
        self.manager = AccountManager(price_provider=self.price_provider)
        self.account = self.manager.create_account("Test Account", 10000.0)

    def test_withdraw_decreases_balance(self) -> None:
        self.manager.withdraw(self.account.account_id, 300.0)
        updated = self.manager.get_account(self.account.account_id)
        self.assertEqual(updated.balance, 9700.0)

    def test_withdraw_records_transaction(self) -> None:
        txn = self.manager.withdraw(self.account.account_id, 400.0)
        self.assertEqual(txn.transaction_type, TransactionType.WITHDRAW)
        self.assertEqual(txn.amount, 400.0)

    def test_withdraw_insufficient_funds_raises(self) -> None:
        with self.assertRaises(ValueError):
            self.manager.withdraw(self.account.account_id, 20000.0)

    def test_withdraw_exact_balance_succeeds(self) -> None:
        txn = self.manager.withdraw(self.account.account_id, 10000.0)
        self.assertEqual(txn.amount, 10000.0)
        updated = self.manager.get_account(self.account.account_id)
        self.assertEqual(updated.balance, 0.0)

    def test_withdraw_zero_amount_raises(self) -> None:
        with self.assertRaises(ValueError):
            self.manager.withdraw(self.account.account_id, 0.0)

    def test_withdraw_negative_amount_raises(self) -> None:
        with self.assertRaises(ValueError):
            self.manager.withdraw(self.account.account_id, -100.0)


# ======================================================================
# TestBuyShares
# ======================================================================


class TestBuyShares(unittest.TestCase):
    """Tests for AccountManager.buy_shares."""

    def setUp(self) -> None:
        self.price_provider = TestSharePriceProvider()
        self.manager = AccountManager(price_provider=self.price_provider)
        self.account = self.manager.create_account("Test Account", 10000.0)

    def test_buy_shares_deducts_balance(self) -> None:
        # AAPL = $150, 10 shares = $1,500
        self.manager.buy_shares(self.account.account_id, "AAPL", 10)
        updated = self.manager.get_account(self.account.account_id)
        self.assertEqual(updated.balance, 8500.0)

    def test_buy_shares_increases_holdings(self) -> None:
        self.manager.buy_shares(self.account.account_id, "AAPL", 10)
        holdings = self.manager.get_holdings(self.account.account_id)
        self.assertEqual(holdings["AAPL"], 10)

    def test_buy_shares_records_transaction(self) -> None:
        txn = self.manager.buy_shares(self.account.account_id, "TSLA", 5)
        self.assertEqual(txn.transaction_type, TransactionType.BUY)
        self.assertEqual(txn.symbol, "TSLA")
        self.assertEqual(txn.quantity, 5)
        self.assertEqual(txn.price_per_share, 250.0)
        self.assertEqual(txn.amount, 1250.0)

    def test_buy_multiple_lots_accumulates(self) -> None:
        self.manager.buy_shares(self.account.account_id, "AAPL", 5)
        self.manager.buy_shares(self.account.account_id, "AAPL", 3)
        holdings = self.manager.get_holdings(self.account.account_id)
        self.assertEqual(holdings["AAPL"], 8)

    def test_buy_zero_quantity_raises(self) -> None:
        with self.assertRaises(ValueError):
            self.manager.buy_shares(self.account.account_id, "AAPL", 0)

    def test_buy_negative_quantity_raises(self) -> None:
        with self.assertRaises(ValueError):
            self.manager.buy_shares(self.account.account_id, "AAPL", -5)

    def test_buy_insufficient_funds_raises(self) -> None:
        # GOOGL is $2,800, buying 10 = $28,000 > $10,000
        with self.assertRaises(ValueError):
            self.manager.buy_shares(self.account.account_id, "GOOGL", 10)

    def test_buy_unknown_symbol_raises(self) -> None:
        with self.assertRaises(ValueError):
            self.manager.buy_shares(self.account.account_id, "XYZ", 10)

    def test_buy_spends_exact_balance_succeeds(self) -> None:
        # Use custom provider where AAPL = $100, deposit exactly $1,000
        pp = TestSharePriceProvider({"AAPL": 100.0})
        mgr = AccountManager(price_provider=pp)
        acc = mgr.create_account("Exact", 1000.0)
        mgr.buy_shares(acc.account_id, "AAPL", 10)
        self.assertEqual(mgr.get_account(acc.account_id).balance, 0.0)


# ======================================================================
# TestSellShares
# ======================================================================


class TestSellShares(unittest.TestCase):
    """Tests for AccountManager.sell_shares."""

    def setUp(self) -> None:
        self.price_provider = TestSharePriceProvider()
        self.manager = AccountManager(price_provider=self.price_provider)
        self.account = self.manager.create_account("Test Account", 10000.0)

    def test_sell_shares_increases_balance(self) -> None:
        # Buy 10 AAPL at $150
        self.manager.buy_shares(self.account.account_id, "AAPL", 10)
        # Sell 5 AAPL at $150
        self.manager.sell_shares(self.account.account_id, "AAPL", 5)
        updated = self.manager.get_account(self.account.account_id)
        # 10000 - 1500 + 750 = 9250
        self.assertEqual(updated.balance, 9250.0)

    def test_sell_shares_decreases_holdings(self) -> None:
        self.manager.buy_shares(self.account.account_id, "AAPL", 10)
        self.manager.sell_shares(self.account.account_id, "AAPL", 3)
        holdings = self.manager.get_holdings(self.account.account_id)
        self.assertEqual(holdings["AAPL"], 7)

    def test_sell_shares_records_transaction(self) -> None:
        self.manager.buy_shares(self.account.account_id, "TSLA", 5)
        txn = self.manager.sell_shares(self.account.account_id, "TSLA", 2)
        self.assertEqual(txn.transaction_type, TransactionType.SELL)
        self.assertEqual(txn.symbol, "TSLA")
        self.assertEqual(txn.quantity, 2)
        self.assertEqual(txn.price_per_share, 250.0)
        self.assertEqual(txn.amount, 500.0)

    def test_sell_partial_holdings(self) -> None:
        self.manager.buy_shares(self.account.account_id, "AAPL", 10)
        self.manager.sell_shares(self.account.account_id, "AAPL", 4)
        holdings = self.manager.get_holdings(self.account.account_id)
        self.assertEqual(holdings["AAPL"], 6)

    def test_sell_all_holdings_removes_symbol(self) -> None:
        self.manager.buy_shares(self.account.account_id, "AAPL", 10)
        self.manager.sell_shares(self.account.account_id, "AAPL", 10)
        holdings = self.manager.get_holdings(self.account.account_id)
        self.assertNotIn("AAPL", holdings)

    def test_sell_zero_quantity_raises(self) -> None:
        with self.assertRaises(ValueError):
            self.manager.sell_shares(self.account.account_id, "AAPL", 0)

    def test_sell_negative_quantity_raises(self) -> None:
        with self.assertRaises(ValueError):
            self.manager.sell_shares(self.account.account_id, "AAPL", -5)

    def test_sell_more_than_held_raises(self) -> None:
        self.manager.buy_shares(self.account.account_id, "AAPL", 5)
        with self.assertRaises(ValueError):
            self.manager.sell_shares(self.account.account_id, "AAPL", 10)

    def test_sell_unheld_symbol_raises(self) -> None:
        # Buy AAPL, then attempt to sell TSLA (known but not held)
        self.manager.buy_shares(self.account.account_id, "AAPL", 10)
        with self.assertRaises(ValueError):
            self.manager.sell_shares(self.account.account_id, "TSLA", 5)

    def test_sell_unknown_symbol_raises(self) -> None:
        # Symbol not in price provider and not held
        with self.assertRaises(ValueError):
            self.manager.sell_shares(self.account.account_id, "XYZ", 5)


# ======================================================================
# TestPortfolioValue
# ======================================================================


class TestPortfolioValue(unittest.TestCase):
    """Tests for AccountManager.get_portfolio_value."""

    def setUp(self) -> None:
        self.price_provider = TestSharePriceProvider()
        self.manager = AccountManager(price_provider=self.price_provider)
        self.account = self.manager.create_account("Test Account", 10000.0)

    def test_portfolio_value_cash_only(self) -> None:
        pv = self.manager.get_portfolio_value(self.account.account_id)
        self.assertEqual(pv, 10000.0)

    def test_portfolio_value_includes_holdings(self) -> None:
        # Buy 10 AAPL at $150
        self.manager.buy_shares(self.account.account_id, "AAPL", 10)
        # Balance = 8500, holdings value = 10 * 150 = 1500
        pv = self.manager.get_portfolio_value(self.account.account_id)
        self.assertEqual(pv, 10000.0)

    def test_portfolio_value_zero_balance_and_holdings(self) -> None:
        account = self.manager.create_account("Empty", 0.0)
        pv = self.manager.get_portfolio_value(account.account_id)
        self.assertEqual(pv, 0.0)

    def test_portfolio_value_after_buy_and_price_change(self) -> None:
        self.manager.buy_shares(self.account.account_id, "AAPL", 10)
        # Simulate price change by mutating the provider's internal dict
        self.manager.price_provider._prices["AAPL"] = 200.0  # type: ignore[index]
        pv = self.manager.get_portfolio_value(self.account.account_id)
        # Balance = 8500, holdings value = 10 * 200 = 2000
        self.assertEqual(pv, 10500.0)


# ======================================================================
# TestProfitLoss
# ======================================================================


class TestProfitLoss(unittest.TestCase):
    """Tests for AccountManager.get_profit_loss.

    Formula: (portfolio_value + total_withdrawn) - total_deposited
    """

    def setUp(self) -> None:
        self.price_provider = TestSharePriceProvider()
        self.manager = AccountManager(price_provider=self.price_provider)
        self.account = self.manager.create_account("Test Account", 10000.0)

    def test_profit_loss_zero_with_no_activity(self) -> None:
        account = self.manager.create_account("Idle", 0.0)
        pnl = self.manager.get_profit_loss(account.account_id)
        self.assertEqual(pnl, 0.0)

    def test_profit_loss_positive_after_gain(self) -> None:
        # Buy 10 AAPL at $150 → $1,500 cost, balance = $8,500
        self.manager.buy_shares(self.account.account_id, "AAPL", 10)
        # Increase AAPL price to $200
        self.manager.price_provider._prices["AAPL"] = 200.0  # type: ignore[index]
        pnl = self.manager.get_profit_loss(self.account.account_id)
        # portfolio_value = 8500 + 10*200 = 10500
        # P&L = (10500 + 0) - 10000 = 500
        self.assertEqual(pnl, 500.0)

    def test_profit_loss_negative_after_loss(self) -> None:
        self.manager.buy_shares(self.account.account_id, "AAPL", 10)
        # Decrease AAPL price to $100
        self.manager.price_provider._prices["AAPL"] = 100.0  # type: ignore[index]
        pnl = self.manager.get_profit_loss(self.account.account_id)
        # portfolio_value = 8500 + 10*100 = 9500
        # P&L = (9500 + 0) - 10000 = -500
        self.assertEqual(pnl, -500.0)

    def test_profit_loss_accounts_for_withdrawals(self) -> None:
        self.manager.withdraw(self.account.account_id, 2000.0)
        pnl = self.manager.get_profit_loss(self.account.account_id)
        # portfolio_value = 8000, total_withdrawn = 2000, total_deposited = 10000
        # P&L = (8000 + 2000) - 10000 = 0
        self.assertEqual(pnl, 0.0)


# ======================================================================
# TestHoldings
# ======================================================================


class TestHoldings(unittest.TestCase):
    """Tests for AccountManager.get_holdings."""

    def setUp(self) -> None:
        self.price_provider = TestSharePriceProvider()
        self.manager = AccountManager(price_provider=self.price_provider)
        self.account = self.manager.create_account("Test Account", 10000.0)

    def test_get_holdings_empty_initially(self) -> None:
        holdings = self.manager.get_holdings(self.account.account_id)
        self.assertEqual(holdings, {})

    def test_get_holdings_returns_only_nonzero(self) -> None:
        self.manager.buy_shares(self.account.account_id, "AAPL", 5)
        self.manager.buy_shares(self.account.account_id, "TSLA", 3)
        self.manager.sell_shares(self.account.account_id, "TSLA", 3)
        holdings = self.manager.get_holdings(self.account.account_id)
        self.assertIn("AAPL", holdings)
        self.assertEqual(holdings["AAPL"], 5)
        self.assertNotIn("TSLA", holdings)  # fully sold

    def test_get_holdings_multiple_symbols(self) -> None:
        self.manager.buy_shares(self.account.account_id, "AAPL", 10)
        self.manager.buy_shares(self.account.account_id, "TSLA", 5)
        self.manager.buy_shares(self.account.account_id, "GOOGL", 1)
        holdings = self.manager.get_holdings(self.account.account_id)
        self.assertEqual(holdings, {"AAPL": 10, "TSLA": 5, "GOOGL": 1})


# ======================================================================
# TestTransactions
# ======================================================================


class TestTransactions(unittest.TestCase):
    """Tests for get_transactions and get_transactions_filtered."""

    def setUp(self) -> None:
        self.price_provider = TestSharePriceProvider()
        self.manager = AccountManager(price_provider=self.price_provider)
        self.account = self.manager.create_account("Test Account", 10000.0)

    def test_get_transactions_chronological(self) -> None:
        self.manager.deposit(self.account.account_id, 500.0)
        self.manager.withdraw(self.account.account_id, 200.0)
        txns = self.manager.get_transactions(self.account.account_id)
        # They should be in order: initial deposit, deposit, withdraw
        types = [t.transaction_type for t in txns]
        self.assertEqual(
            types,
            [
                TransactionType.DEPOSIT,  # initial
                TransactionType.DEPOSIT,  # extra deposit
                TransactionType.WITHDRAW,
            ],
        )

    def test_get_transactions_filtered_by_type(self) -> None:
        self.manager.deposit(self.account.account_id, 500.0)
        self.manager.withdraw(self.account.account_id, 200.0)
        self.manager.buy_shares(self.account.account_id, "AAPL", 5)

        deposits = self.manager.get_transactions_filtered(
            self.account.account_id, transaction_type="deposit"
        )
        self.assertEqual(len(deposits), 2)  # initial + extra
        self.assertTrue(
            all(t.transaction_type == TransactionType.DEPOSIT for t in deposits)
        )

        buys = self.manager.get_transactions_filtered(
            self.account.account_id, transaction_type=TransactionType.BUY
        )
        self.assertEqual(len(buys), 1)
        self.assertEqual(buys[0].symbol, "AAPL")

    def test_get_transactions_filtered_by_symbol(self) -> None:
        self.manager.buy_shares(self.account.account_id, "AAPL", 5)
        self.manager.buy_shares(self.account.account_id, "TSLA", 3)
        self.manager.buy_shares(self.account.account_id, "AAPL", 2)

        aapl_txns = self.manager.get_transactions_filtered(
            self.account.account_id, symbol="AAPL"
        )
        self.assertEqual(len(aapl_txns), 2)
        self.assertTrue(all(t.symbol == "AAPL" for t in aapl_txns))

        tsla_txns = self.manager.get_transactions_filtered(
            self.account.account_id, symbol="tsla"
        )
        self.assertEqual(len(tsla_txns), 1)
        self.assertEqual(tsla_txns[0].symbol, "TSLA")

    def test_get_transactions_filtered_by_time_range(self) -> None:
        before_deposit = datetime.now(timezone.utc)
        self.manager.deposit(self.account.account_id, 500.0)
        after_deposit = datetime.now(timezone.utc)
        self.manager.withdraw(self.account.account_id, 200.0)
        after_withdraw = datetime.now(timezone.utc)

        # Transactions at or after after_deposit (should be only the withdraw)
        after_t1 = self.manager.get_transactions_filtered(
            self.account.account_id, start_time=after_deposit
        )
        self.assertEqual(len(after_t1), 1)
        self.assertEqual(after_t1[0].transaction_type, TransactionType.WITHDRAW)

        # Transactions up to after_deposit (initial deposit + extra deposit)
        up_to = self.manager.get_transactions_filtered(
            self.account.account_id, end_time=after_deposit
        )
        deposit_count = sum(
            1 for t in up_to if t.transaction_type == TransactionType.DEPOSIT
        )
        self.assertEqual(deposit_count, 2)

        # Transactions between before_deposit and after_deposit: deposit only
        between = self.manager.get_transactions_filtered(
            self.account.account_id,
            start_time=before_deposit,
            end_time=after_deposit,
        )
        deposit_types = [t.transaction_type for t in between]
        self.assertIn(TransactionType.DEPOSIT, deposit_types)


# ======================================================================
# TestTransactionSerialization
# ======================================================================


class TestTransactionSerialization(unittest.TestCase):
    """Tests for Transaction.to_dict and Transaction.from_dict roundtrip."""

    def test_transaction_to_dict_and_from_dict_roundtrip(self) -> None:
        # Create a transaction using a factory
        txn = Transaction.create_deposit(1500.0, "acct-123")
        data = txn.to_dict()
        restored = Transaction.from_dict(data)

        self.assertEqual(restored.transaction_id, txn.transaction_id)
        self.assertEqual(restored.transaction_type, txn.transaction_type)
        self.assertEqual(restored.symbol, txn.symbol)
        self.assertEqual(restored.quantity, txn.quantity)
        self.assertEqual(restored.price_per_share, txn.price_per_share)
        self.assertEqual(restored.amount, txn.amount)
        self.assertEqual(restored.account_id, txn.account_id)
        # Timestamps should match (isoformat roundtrip may lose microsecond
        # precision in edge cases but typically preserves it)
        self.assertEqual(
            restored.timestamp.isoformat(), txn.timestamp.isoformat()
        )

        # Also test a BUY transaction for full coverage of non-None fields
        buy_txn = Transaction.create_buy("AAPL", 10, 150.0, "acct-456")
        buy_data = buy_txn.to_dict()
        buy_restored = Transaction.from_dict(buy_data)

        self.assertEqual(buy_restored.transaction_id, buy_txn.transaction_id)
        self.assertEqual(buy_restored.transaction_type, TransactionType.BUY)
        self.assertEqual(buy_restored.symbol, "AAPL")
        self.assertEqual(buy_restored.quantity, 10)
        self.assertEqual(buy_restored.price_per_share, 150.0)
        self.assertEqual(buy_restored.amount, 1500.0)
        self.assertEqual(buy_restored.account_id, "acct-456")

        # Test SELL transaction too
        sell_txn = Transaction.create_sell("TSLA", 5, 250.0, "acct-789")
        sell_data = sell_txn.to_dict()
        sell_restored = Transaction.from_dict(sell_data)

        self.assertEqual(sell_restored.transaction_type, TransactionType.SELL)
        self.assertEqual(sell_restored.symbol, "TSLA")
        self.assertEqual(sell_restored.quantity, 5)
        self.assertEqual(sell_restored.amount, 1250.0)


# ======================================================================
# TestAccountSerialization
# ======================================================================


class TestAccountSerialization(unittest.TestCase):
    """Tests for Account.to_dict and Account.from_dict roundtrip."""

    def test_account_to_dict_and_from_dict_roundtrip(self) -> None:
        manager = AccountManager()
        account = manager.create_account("SerializeMe", 5000.0)
        manager.deposit(account.account_id, 1000.0)
        manager.buy_shares(account.account_id, "AAPL", 5)

        data = account.to_dict()

        # Verify dict keys
        self.assertIn("account_id", data)
        self.assertIn("name", data)
        self.assertIn("balance", data)
        self.assertIn("holdings", data)
        self.assertIn("transaction_count", data)
        self.assertIn("initial_deposit", data)
        self.assertIn("total_deposited", data)
        self.assertIn("total_withdrawn", data)
        self.assertIn("created_at", data)

        self.assertEqual(data["name"], "SerializeMe")
        self.assertEqual(data["balance"], 6000.0 - 5 * 150.0)  # 6000 - 750 = 5250
        self.assertEqual(data["holdings"], {"AAPL": 5})
        self.assertEqual(data["transaction_count"], 3)  # initial deposit + deposit + buy
        self.assertEqual(data["initial_deposit"], 5000.0)
        self.assertEqual(data["total_deposited"], 6000.0)

        # Reconstruct and verify key fields
        restored = Account.from_dict(data)
        self.assertEqual(restored.account_id, account.account_id)
        self.assertEqual(restored.name, account.name)
        self.assertEqual(restored.balance, account.balance)
        self.assertEqual(restored.holdings, account.holdings)
        self.assertEqual(restored.initial_deposit, account.initial_deposit)
        self.assertEqual(restored.total_deposited, account.total_deposited)
        self.assertEqual(restored.total_withdrawn, account.total_withdrawn)
        # Transactions are not preserved in from_dict (set to empty list)
        self.assertEqual(restored.transactions, [])


# ======================================================================
# TestSharePriceProviderClass
# ======================================================================


class TestSharePriceProviderClass(unittest.TestCase):
    """Tests for the TestSharePriceProvider class itself."""

    def test_returns_fixed_price_for_aapl(self) -> None:
        pp = TestSharePriceProvider()
        self.assertEqual(pp.get_share_price("AAPL"), 150.0)

    def test_returns_fixed_price_for_tsla(self) -> None:
        pp = TestSharePriceProvider()
        self.assertEqual(pp.get_share_price("TSLA"), 250.0)

    def test_returns_fixed_price_for_googl(self) -> None:
        pp = TestSharePriceProvider()
        self.assertEqual(pp.get_share_price("GOOGL"), 2800.0)

    def test_unknown_symbol_raises(self) -> None:
        pp = TestSharePriceProvider()
        with self.assertRaises(ValueError):
            pp.get_share_price("UNKNOWN")

    def test_custom_prices(self) -> None:
        pp = TestSharePriceProvider(prices={"MSFT": 300.0, "aapl": 999.0})
        # Custom override for AAPL
        self.assertEqual(pp.get_share_price("AAPL"), 999.0)
        # Custom new symbol
        self.assertEqual(pp.get_share_price("MSFT"), 300.0)
        # Default still works for others
        self.assertEqual(pp.get_share_price("TSLA"), 250.0)


# ======================================================================
# TestDefaultManager
# ======================================================================


class TestDefaultManager(unittest.TestCase):
    """Tests for module-level get_default_manager and reset_manager."""

    def setUp(self) -> None:
        # Ensure we start with a clean slate
        reset_manager()

    def tearDown(self) -> None:
        # Clean up after each test
        reset_manager()

    def test_get_default_manager_returns_singleton(self) -> None:
        mgr1 = get_default_manager()
        mgr2 = get_default_manager()
        self.assertIs(mgr1, mgr2)

    def test_reset_manager_creates_new_instance(self) -> None:
        mgr1 = get_default_manager()
        reset_manager()
        mgr2 = get_default_manager()
        self.assertIsNot(mgr1, mgr2)

    def test_default_manager_is_usable(self) -> None:
        """Verify the default manager works like any AccountManager."""
        mgr = get_default_manager()
        account = mgr.create_account("DefaultUser", 1000.0)
        self.assertEqual(account.balance, 1000.0)
        mgr.deposit(account.account_id, 500.0)
        self.assertEqual(mgr.get_account(account.account_id).balance, 1500.0)


# ======================================================================
# TestAccountSummary
# ======================================================================


class TestAccountSummary(unittest.TestCase):
    """Tests for get_account_summary and get_all_account_summaries."""

    def setUp(self) -> None:
        self.price_provider = TestSharePriceProvider()
        self.manager = AccountManager(price_provider=self.price_provider)
        self.account = self.manager.create_account("SummaryAccount", 10000.0)

    def test_get_account_summary_keys(self) -> None:
        summary = self.manager.get_account_summary(self.account.account_id)
        expected_keys = {
            "account_id",
            "name",
            "balance",
            "holdings",
            "portfolio_value",
            "profit_loss",
            "total_deposited",
            "total_withdrawn",
            "transaction_count",
        }
        self.assertEqual(set(summary.keys()), expected_keys)

    def test_get_account_summary_values_cash_only(self) -> None:
        summary = self.manager.get_account_summary(self.account.account_id)
        self.assertEqual(summary["account_id"], self.account.account_id)
        self.assertEqual(summary["name"], "SummaryAccount")
        self.assertEqual(summary["balance"], 10000.0)
        self.assertEqual(summary["holdings"], {})
        self.assertEqual(summary["portfolio_value"], 10000.0)
        self.assertEqual(summary["profit_loss"], 0.0)
        self.assertEqual(summary["total_deposited"], 10000.0)
        self.assertEqual(summary["total_withdrawn"], 0.0)
        self.assertEqual(summary["transaction_count"], 1)  # initial deposit

    def test_get_account_summary_after_activity(self) -> None:
        self.manager.buy_shares(self.account.account_id, "AAPL", 10)
        self.manager.withdraw(self.account.account_id, 1000.0)
        summary = self.manager.get_account_summary(self.account.account_id)

        self.assertEqual(summary["balance"], 10000.0 - 1500.0 - 1000.0)  # 7500
        self.assertEqual(summary["holdings"], {"AAPL": 10})
        # portfolio_value = 7500 + 10*150 = 9000
        self.assertEqual(summary["portfolio_value"], 9000.0)
        # P&L = (9000 + 1000) - 10000 = 0
        self.assertEqual(summary["profit_loss"], 0.0)
        self.assertEqual(summary["total_deposited"], 10000.0)
        self.assertEqual(summary["total_withdrawn"], 1000.0)
        self.assertEqual(summary["transaction_count"], 3)  # init+ buy + withdraw

    def test_get_all_account_summaries(self) -> None:
        self.manager.create_account("Second", 500.0)
        self.manager.create_account("Third", 200.0)
        summaries = self.manager.get_all_account_summaries()
        self.assertEqual(len(summaries), 3)
        names = {s["name"] for s in summaries}
        self.assertEqual(names, {"SummaryAccount", "Second", "Third"})

        # Verify each summary has the required keys
        for s in summaries:
            self.assertIn("account_id", s)
            self.assertIn("name", s)
            self.assertIn("balance", s)
            self.assertIn("portfolio_value", s)
            self.assertIn("profit_loss", s)

    def test_get_all_account_summaries_empty(self) -> None:
        # Fresh manager with no accounts
        mgr = AccountManager(price_provider=self.price_provider)
        summaries = mgr.get_all_account_summaries()
        self.assertEqual(summaries, [])


# ======================================================================
# TestSharePriceProviderAbstract
# ======================================================================


class TestSharePriceProviderAbstract(unittest.TestCase):
    """Tests for the abstract SharePriceProvider base class."""

    def test_abstract_get_share_price_raises(self) -> None:
        spp = SharePriceProvider()
        with self.assertRaises(NotImplementedError):
            spp.get_share_price("AAPL")


# ======================================================================
# Main entry point
# ======================================================================

if __name__ == "__main__":
    unittest.main()
```

---

## Summary of Results

| Metric | Value |
|---|---|
| **Test framework** | Python stdlib `unittest` |
| **Test classes** | 16 |
| **Test methods** | 70 |
| **Passed** | 70 ✅ |
| **Failed** | 0 |
| **Errors** | 0 |
| **Backend changes required** | None |

### Test Class Breakdown

| Test Class | Tests | Coverage |
|---|---|---|
| `TestAccountCreation` | 10 | create, list, get, delete, validation |
| `TestDeposit` | 4 | balance increase, transaction recording, validation |
| `TestWithdrawal` | 6 | balance decrease, exact balance, insufficient funds, validation |
| `TestBuyShares` | 9 | balance deduction, holdings, multiple lots, exact balance, validation |
| `TestSellShares` | 10 | balance increase, partial/full sale, symbol removal, validation |
| `TestPortfolioValue` | 4 | cash-only, with holdings, zero balance, price changes |
| `TestProfitLoss` | 4 | no activity, gain, loss, withdrawals accounted |
| `TestHoldings` | 3 | empty, nonzero only, multiple symbols |
| `TestTransactions` | 4 | chronological, filtered by type/symbol/time |
| `TestTransactionSerialization` | 1 | to_dict/from_dict roundtrip (deposit, buy, sell) |
| `TestAccountSerialization` | 1 | to_dict/from_dict roundtrip |
| `TestSharePriceProviderClass` | 5 | fixed prices, unknown symbol, custom prices |
| `TestDefaultManager` | 3 | singleton, reset, usability |
| `TestAccountSummary` | 4 | keys, values, after activity, all summaries, empty |
| `TestSharePriceProviderAbstract` | 1 | NotImplementedError raised |

### How to Run

```bash
cd /home/user/sandbox
python -m unittest test_portfolio_manager.py -v
```

**No backend code changes were needed** — `portfolio_manager.py` and `app.py` remain untouched. All 70 unit tests pass against the existing backend implementation.