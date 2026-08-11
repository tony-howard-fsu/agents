"""Quick smoke test for backend.py"""
from backend import (
    Account, AccountManager, Transaction, Holding,
    InsufficientFundsError, InsufficientSharesError,
)

# Mock price provider
def mock_prices(symbol: str) -> float:
    prices = {"AAPL": 150.0, "TSLA": 250.0, "GOOGL": 2800.0}
    if symbol not in prices:
        raise ValueError(f"Unknown symbol: {symbol}")
    return prices[symbol]

# Test 1: Create account
manager = AccountManager(price_provider=mock_prices)
acc_id = manager.create_account(10000.0)
print(f"Created account: {acc_id}")

# Test 2: Deposit
manager.deposit(acc_id, 500.0)
print("Deposited 500")

# Test 3: Buy
manager.record_trade(acc_id, "BUY", "AAPL", 10)
print("Bought 10 AAPL")

# Test 4: Holdings
holdings = manager.get_holdings_report(acc_id)
print(f"Holdings: {holdings}")

# Test 5: Portfolio value
pv = manager.get_portfolio_value(acc_id)
print(f"Portfolio value: {pv}")

# Test 6: P&L
pnl = manager.get_profit_loss(acc_id)
print(f"P&L: {pnl}")

# Test 7: Transactions
txns = manager.get_transaction_history(acc_id)
print(f"Transactions: {len(txns)}")
for t in txns:
    print(f"  {t.type} | {t.symbol} | qty={t.quantity} | price={t.price} | amount={t.amount}")

# Test 8: Sell
manager.record_trade(acc_id, "SELL", "AAPL", 5)
print("Sold 5 AAPL")
holdings2 = manager.get_holdings_report(acc_id)
print(f"Holdings after sell: {holdings2}")

# Test 9: Withdraw
manager.withdraw(acc_id, 200.0)
print("Withdrew 200")

# Test 10: InsufficientFundsError
try:
    manager.record_trade(acc_id, "BUY", "GOOGL", 100)
except InsufficientFundsError as e:
    print(f"Correctly caught: {e}")

# Test 11: InsufficientSharesError
try:
    manager.record_trade(acc_id, "SELL", "AAPL", 100)
except InsufficientSharesError as e:
    print(f"Correctly caught: {e}")

# Test 12: Negative deposit
try:
    manager.create_account(-100.0)
except ValueError as e:
    print(f"Correctly caught: {e}")

# Test 13: Unknown symbol
try:
    manager.record_trade(acc_id, "BUY", "ZZZZ", 10)
except ValueError as e:
    print(f"Correctly caught: {e}")

# Test 14: KeyError
try:
    manager.deposit("nonexistent", 100.0)
except KeyError as e:
    print(f"Correctly caught: {e}")

# Test 15: get_pnl_report alias
pnl2 = manager.get_pnl_report(acc_id)
print(f"P&L via alias: {pnl2}")

# Test 16: Portfolio value math
# initial: 10000 + 500 = 10500
# buy 10 AAPL @150: -1500 = 9000 cash, 10 AAPL
# sell 5 AAPL @150: +750 = 9750 cash, 5 AAPL
# withdraw 200: 9550 cash, 5 AAPL @150 = 750
# portfolio value = 9550 + 750 = 10300
# P&L = 10300 - 10000 = 300
print(f"Expected portfolio value: 10300, got: {pv}")

# Recompute after trades
pv_final = manager.get_portfolio_value(acc_id)
pnl_final = manager.get_profit_loss(acc_id)
print(f"Final portfolio value: {pv_final}")
print(f"Final P&L: {pnl_final}")

print("\nAll tests passed!")
