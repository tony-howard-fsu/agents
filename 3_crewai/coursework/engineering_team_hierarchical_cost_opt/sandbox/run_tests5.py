print("STARTING TESTS...")
import unittest
import sys

from backend import (
    Account,
    AccountManager,
    Transaction,
    Holding,
    InsufficientFundsError,
    InsufficientSharesError,
)
from unittest.mock import MagicMock
from datetime import datetime


# Just run a single test directly
manager = AccountManager(price_provider=lambda s: {"AAPL": 150.0, "TSLA": 250.0, "GOOGL": 140.0}[s])
acc_id = manager.create_account(0.0)
assert isinstance(acc_id, str) and len(acc_id) > 0
assert manager.get_portfolio_value(acc_id) == 0.0
assert manager.get_transaction_history(acc_id) == []
print("Test 1 passed: zero deposit")

acc_id2 = manager.create_account(1000.0)
assert manager.get_portfolio_value(acc_id2) == 1000.0
txn_list = manager.get_transaction_history(acc_id2)
assert len(txn_list) == 1
assert txn_list[0].type == "DEPOSIT"
assert txn_list[0].amount == 1000.0
print("Test 2 passed: positive deposit")

try:
    manager.create_account(-100.0)
    assert False, "Should have raised"
except ValueError:
    pass
print("Test 3 passed: negative deposit raises ValueError")

# Now run with unittest
loader = unittest.TestLoader()
suite = loader.loadTestsFromName("test_backend")
runner = unittest.TextTestRunner(verbosity=2)
result = runner.run(suite)

print("Tests run:", result.testsRun)
print("Errors:", len(result.errors))
print("Failures:", len(result.failures))
print("Success:", result.wasSuccessful())
