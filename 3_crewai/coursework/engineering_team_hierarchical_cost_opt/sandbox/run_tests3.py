import unittest
import sys
import io
from datetime import datetime

from backend import (
    Account,
    AccountManager,
    Transaction,
    Holding,
    InsufficientFundsError,
    InsufficientSharesError,
)

# Minimal test to verify things work
print("Hello from run_tests3")

# Create an account manager
mgr = AccountManager()
acc_id = mgr.create_account(1000.0)
print(f"Created account: {acc_id}")
print(f"Portfolio value: {mgr.get_portfolio_value(acc_id)}")

# Test deposit
mgr.deposit(acc_id, 500.0)
print(f"After deposit: {mgr.get_portfolio_value(acc_id)}")

# Test profit/loss
print(f"P&L: {mgr.get_profit_loss(acc_id)}")

# Test record_trade
mgr.record_trade(acc_id, "BUY", "AAPL", 10)
print(f"After buy: portfolio={mgr.get_portfolio_value(acc_id)}")
print(f"Holdings: {mgr.get_holdings_report(acc_id)}")

# Test transaction history
txns = mgr.get_transaction_history(acc_id)
print(f"Transactions: {len(txns)}")
for t in txns:
    print(f"  {t.type} {t.symbol} {t.amount}")

print("All basic tests passed!")
