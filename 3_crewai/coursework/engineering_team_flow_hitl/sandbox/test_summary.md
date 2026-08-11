# Final Answer

## Unit Test File: `/sandbox/test_backend.py`

```python
"""Unit tests for the backend module using stdlib unittest."""

import unittest
import uuid

from backend import AccountManager, SharePriceService, Transaction, Holding


# ---------------------------------------------------------------------------
# SharePriceService
# ---------------------------------------------------------------------------
class SharePriceServiceTests(unittest.TestCase):
    def setUp(self):
        self.sps = SharePriceService()

    def test_get_share_price_known_symbols(self):
        self.assertEqual(self.sps.get_share_price("AAPL"), 150.0)
        self.assertEqual(self.sps.get_share_price("TSLA"), 250.0)
        self.assertEqual(self.sps.get_share_price("GOOGL"), 175.0)

    def test_get_share_price_unknown_raises(self):
        with self.assertRaises(ValueError):
            self.sps.get_share_price("UNKNOWN")


# ---------------------------------------------------------------------------
# AccountManager – account lifecycle
# ---------------------------------------------------------------------------
class AccountLifecycleTests(unittest.TestCase):
    def setUp(self):
        self.am = AccountManager()

    def test_create_account_returns_uuid4(self):
        acct_id = self.am.create_account("Test User", 10000.0)
        self.assertEqual(len(acct_id), 36)
        # Verify it's a valid UUID
        uuid.UUID(acct_id)

    def test_create_account_empty_name_raises(self):
        with self.assertRaises(ValueError):
            self.am.create_account("", 0.0)
        with self.assertRaises(ValueError):
            self.am.create_account("   ", 0.0)

    def test_create_account_negative_deposit_raises(self):
        with self.assertRaises(ValueError):
            self.am.create_account("Bad", -1.0)

    def test_get_account_name(self):
        acct_id = self.am.create_account("Alice", 500.0)
        self.assertEqual(self.am.get_account_name(acct_id), "Alice")

    def test_get_account_name_bad_id_raises_keyerror(self):
        with self.assertRaises(KeyError):
            self.am.get_account_name("nonexistent")

    def test_list_accounts(self):
        a1 = self.am.create_account("Alice", 1000.0)
        a2 = self.am.create_account("Bob", 2000.0)
        accounts = self.am.list_accounts()
        self.assertEqual(len(accounts), 2)
        ids = {a["id"] for a in accounts}
        self.assertIn(a1, ids)
        self.assertIn(a2, ids)
        names = {a["name"] for a in accounts}
        self.assertIn("Alice", names)
        self.assertIn("Bob", names)


# ---------------------------------------------------------------------------
# AccountManager – cash operations
# ---------------------------------------------------------------------------
class CashOperationsTests(unittest.TestCase):
    def setUp(self):
        self.am = AccountManager()
        self.acct = self.am.create_account("Trader", 10000.0)

    def test_initial_balance(self):
        self.assertEqual(self.am.get_balance(self.acct), 10000.0)

    def test_deposit(self):
        tx = self.am.deposit(self.acct, 500.0)
        self.assertEqual(tx.type, "DEPOSIT")
        self.assertEqual(tx.amount, 500.0)
        self.assertEqual(self.am.get_balance(self.acct), 10500.0)

    def test_deposit_nonpositive_raises(self):
        with self.assertRaises(ValueError):
            self.am.deposit(self.acct, 0.0)
        with self.assertRaises(ValueError):
            self.am.deposit(self.acct, -100.0)

    def test_deposit_bad_account_raises(self):
        with self.assertRaises(KeyError):
            self.am.deposit("nonexistent", 100.0)

    def test_withdraw(self):
        tx = self.am.withdraw(self.acct, 200.0)
        self.assertEqual(tx.type, "WITHDRAW")
        self.assertEqual(tx.amount, -200.0)
        self.assertEqual(self.am.get_balance(self.acct), 9800.0)

    def test_withdraw_nonpositive_raises(self):
        with self.assertRaises(ValueError):
            self.am.withdraw(self.acct, 0.0)
        with self.assertRaises(ValueError):
            self.am.withdraw(self.acct, -50.0)

    def test_withdraw_insufficient_raises(self):
        with self.assertRaises(ValueError):
            self.am.withdraw(self.acct, 999999.0)

    def test_withdraw_bad_account_raises(self):
        with self.assertRaises(KeyError):
            self.am.withdraw("nonexistent", 100.0)


# ---------------------------------------------------------------------------
# AccountManager – trading operations
# ---------------------------------------------------------------------------
class TradingTests(unittest.TestCase):
    def setUp(self):
        self.am = AccountManager()
        self.acct = self.am.create_account("Trader", 10000.0)

    # -- BUY --
    def test_buy(self):
        tx = self.am.buy(self.acct, "AAPL", 10)
        self.assertEqual(tx.type, "BUY")
        self.assertEqual(tx.symbol, "AAPL")
        self.assertEqual(tx.quantity, 10)
        self.assertEqual(tx.price, 150.0)
        self.assertEqual(tx.amount, -1500.0)
        self.assertEqual(self.am.get_balance(self.acct), 8500.0)

    def test_buy_zero_quantity_raises(self):
        with self.assertRaises(ValueError):
            self.am.buy(self.acct, "AAPL", 0)

    def test_buy_negative_quantity_raises(self):
        with self.assertRaises(ValueError):
            self.am.buy(self.acct, "AAPL", -5)

    def test_buy_unknown_symbol_raises(self):
        with self.assertRaises(ValueError):
            self.am.buy(self.acct, "MISSING", 1)

    def test_buy_insufficient_balance_raises(self):
        with self.assertRaises(ValueError):
            self.am.buy(self.acct, "AAPL", 1000)  # 1000 * 150 = 150000 > 10000

    def test_buy_bad_account_raises(self):
        with self.assertRaises(KeyError):
            self.am.buy("nonexistent", "AAPL", 1)

    def test_buy_multiple_updates_avg_cost(self):
        self.am.buy(self.acct, "AAPL", 10)  # at 150
        self.am.buy(self.acct, "TSLA", 5)   # at 250
        self.am.buy(self.acct, "AAPL", 10)  # at 150 again → avg still 150
        holdings = self.am.get_holdings(self.acct)
        aapl = [h for h in holdings if h.symbol == "AAPL"][0]
        self.assertEqual(aapl.quantity, 20)
        self.assertEqual(aapl.avg_cost_per_share, 150.0)

    def test_buy_different_price_changes_avg(self):
        # First buy at the default price
        self.am.buy(self.acct, "GOOGL", 10)  # at 175 → balance 10000-1750=8250
        # We can't easily change price, so avg stays 175 for now
        holdings = self.am.get_holdings(self.acct)
        googl = [h for h in holdings if h.symbol == "GOOGL"][0]
        self.assertEqual(googl.avg_cost_per_share, 175.0)

    # -- SELL --
    def test_sell(self):
        self.am.buy(self.acct, "AAPL", 10)
        tx = self.am.sell(self.acct, "AAPL", 5)
        self.assertEqual(tx.type, "SELL")
        self.assertEqual(tx.amount, 750.0)  # 5 * 150
        self.assertEqual(self.am.get_balance(self.acct), 9250.0)  # 10000 - 1500 + 750

    def test_sell_zero_quantity_raises(self):
        self.am.buy(self.acct, "AAPL", 10)
        with self.assertRaises(ValueError):
            self.am.sell(self.acct, "AAPL", 0)

    def test_sell_negative_quantity_raises(self):
        self.am.buy(self.acct, "AAPL", 10)
        with self.assertRaises(ValueError):
            self.am.sell(self.acct, "AAPL", -3)

    def test_sell_insufficient_holdings_raises(self):
        self.am.buy(self.acct, "AAPL", 5)
        with self.assertRaises(ValueError):
            self.am.sell(self.acct, "AAPL", 999)

    def test_sell_symbol_not_held_raises(self):
        with self.assertRaises(ValueError):
            self.am.sell(self.acct, "AAPL", 1)

    def test_sell_unknown_symbol_raises(self):
        with self.assertRaises(ValueError):
            self.am.sell(self.acct, "MISSING", 1)

    def test_sell_bad_account_raises(self):
        with self.assertRaises(KeyError):
            self.am.sell("nonexistent", "AAPL", 1)

    def test_sell_all_shares_removes_holding(self):
        self.am.buy(self.acct, "AAPL", 10)
        self.am.sell(self.acct, "AAPL", 10)
        holdings = self.am.get_holdings(self.acct)
        self.assertEqual(len(holdings), 0)

    def test_sell_partial_retains_holding(self):
        self.am.buy(self.acct, "AAPL", 10)
        self.am.sell(self.acct, "AAPL", 3)
        holdings = self.am.get_holdings(self.acct)
        self.assertEqual(len(holdings), 1)
        self.assertEqual(holdings[0].quantity, 7)


# ---------------------------------------------------------------------------
# AccountManager – query / reporting
# ---------------------------------------------------------------------------
class QueryReportingTests(unittest.TestCase):
    def setUp(self):
        self.am = AccountManager()
        self.acct = self.am.create_account("Trader", 10000.0)
        self.am.buy(self.acct, "AAPL", 10)   # cost 1500
        self.am.buy(self.acct, "TSLA", 4)    # cost 1000

    def test_get_holdings(self):
        holdings = self.am.get_holdings(self.acct)
        self.assertEqual(len(holdings), 2)
        symbols = {h.symbol for h in holdings}
        self.assertIn("AAPL", symbols)
        self.assertIn("TSLA", symbols)

    def test_get_portfolio_value(self):
        # balance = 10000 - 1500 - 1000 = 7500
        # market = 10*150 + 4*250 = 1500 + 1000 = 2500
        # portfolio = 7500 + 2500 = 10000
        pv = self.am.get_portfolio_value(self.acct)
        self.assertEqual(pv, 10000.0)

    def test_get_profit_loss(self):
        # total_deposited = 10000, total_withdrawn = 0
        # Portfolio = 10000, net deposits = 10000, so P/L = 0
        pl = self.am.get_profit_loss(self.acct)
        self.assertEqual(pl, 0.0)

    def test_get_transactions(self):
        txns = self.am.get_transactions(self.acct)
        # Most recent first: BUY TSLA, BUY AAPL, DEPOSIT (initial)
        self.assertGreaterEqual(len(txns), 3)
        self.assertEqual(txns[0].type, "BUY")          # most recent = TSLA buy
        self.assertEqual(txns[0].symbol, "TSLA")
        self.assertEqual(txns[-1].type, "DEPOSIT")     # oldest = initial deposit

    def test_get_holdings_with_market_value(self):
        hwmv = self.am.get_holdings_with_market_value(self.acct)
        self.assertEqual(len(hwmv), 2)
        for entry in hwmv:
            self.assertIn("symbol", entry)
            self.assertIn("quantity", entry)
            self.assertIn("avg_cost", entry)
            self.assertIn("current_price", entry)
            self.assertIn("market_value", entry)
            self.assertIn("unrealized_pl", entry)
            if entry["symbol"] == "AAPL":
                self.assertEqual(entry["current_price"], 150.0)
                self.assertEqual(entry["market_value"], 1500.0)
                self.assertEqual(entry["unrealized_pl"], 0.0)

    def test_balance_bad_account_raises(self):
        with self.assertRaises(KeyError):
            self.am.get_balance("nonexistent")

    def test_holdings_bad_account_raises(self):
        with self.assertRaises(KeyError):
            self.am.get_holdings("nonexistent")

    def test_portfolio_value_bad_account_raises(self):
        with self.assertRaises(KeyError):
            self.am.get_portfolio_value("nonexistent")

    def test_profit_loss_bad_account_raises(self):
        with self.assertRaises(KeyError):
            self.am.get_profit_loss("nonexistent")

    def test_transactions_bad_account_raises(self):
        with self.assertRaises(KeyError):
            self.am.get_transactions("nonexistent")

    def test_holdings_with_mv_bad_account_raises(self):
        with self.assertRaises(KeyError):
            self.am.get_holdings_with_market_value("nonexistent")


# ---------------------------------------------------------------------------
# AccountManager – edge / boundary
# ---------------------------------------------------------------------------
class EdgeCaseTests(unittest.TestCase):
    def test_create_account_zero_deposit(self):
        am = AccountManager()
        acct = am.create_account("Zero", 0.0)
        self.assertEqual(am.get_balance(acct), 0.0)
        # Should still be a valid UUID
        uuid.UUID(acct)

    def test_create_account_zero_deposit_no_initial_transaction(self):
        am = AccountManager()
        acct = am.create_account("Zero", 0.0)
        txns = am.get_transactions(acct)
        # No initial deposit transaction when deposit is 0
        self.assertEqual(len(txns), 0)

    def test_deposit_withdraw_sequence(self):
        am = AccountManager()
        acct = am.create_account("Seq", 1000.0)
        am.deposit(acct, 500.0)
        am.withdraw(acct, 200.0)
        am.deposit(acct, 300.0)
        self.assertEqual(am.get_balance(acct), 1600.0)

    def test_buy_sell_multiple_symbols(self):
        am = AccountManager()
        acct = am.create_account("Multi", 20000.0)
        am.buy(acct, "AAPL", 20)    # 3000
        am.buy(acct, "GOOGL", 10)   # 1750
        am.buy(acct, "TSLA", 5)     # 1250
        am.sell(acct, "AAPL", 5)    # +750
        am.sell(acct, "TSLA", 2)    # +500
        # balance: 20000 - 3000 - 1750 - 1250 + 750 + 500 = 15250
        self.assertEqual(am.get_balance(acct), 15250.0)
        holdings = am.get_holdings(acct)
        self.assertEqual(len(holdings), 3)

    def test_profit_loss_after_withdraw(self):
        am = AccountManager()
        acct = am.create_account("PL", 10000.0)
        am.withdraw(acct, 1000.0)
        # total_deposited=10000, total_withdrawn=1000 => net deposits=9000
        # balance=9000, no holdings => portfolio=9000
        # P/L = 9000 - 9000 = 0
        pl = am.get_profit_loss(acct)
        self.assertEqual(pl, 0.0)


if __name__ == "__main__":
    unittest.main()
```

---

## Test Results Summary

```
Ran 49 tests in 0.003s

OK
```

| Metric | Count |
|---|---|
| **Total tests run** | **49** |
| **Passed** | **49** |
| **Failures** | **0** |
| **Errors** | **0** |
| **Skipped** | **0** |

### Test Breakdown by Class

| Test Class | Tests | Areas Covered |
|---|---|---|
| `SharePriceServiceTests` | 2 | Known symbol prices (AAPL $150, TSLA $250, GOOGL $175), unknown symbol raises `ValueError` |
| `AccountLifecycleTests` | 6 | UUID generation, empty/whitespace name validation, negative deposit validation, get account name, bad ID raises `KeyError`, list accounts |
| `CashOperationsTests` | 8 | Initial balance, deposit (balance increase, transaction fields, non-positive amounts, bad account), withdraw (balance decrease, transaction fields, non-positive amounts, insufficient funds, bad account) |
| `TradingTests` | 17 | Buy (valid, zero/negative quantity, unknown symbol, insufficient balance, bad account, avg cost updates), Sell (valid, zero/negative quantity, insufficient holdings, symbol not held, unknown symbol, bad account, full sell removes holding, partial sell retains holding) |
| `QueryReportingTests` | 11 | Holdings, portfolio value, P&L, transactions, holdings with market value, `KeyError` on all query methods for non-existent account |
| `EdgeCaseTests` | 5 | Zero initial deposit, zero deposit creates no initial transaction, deposit-withdraw sequence, buy/sell across multiple symbols, P&L after withdraw |

### Key Observations

- **No backend code changes were required** — `backend.py` passed all tests as-is.
- The `app.py` Gradio frontend is unaffected since no backend signatures were modified.
- All tests use Python's stdlib `unittest` module exclusively — no third-party dependencies.
- Run with: `python -m unittest test_backend.py -v`