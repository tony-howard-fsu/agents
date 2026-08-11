import sys
sys.stdout = open('/tmp/out.txt', 'w')
sys.stderr = open('/tmp/err.txt', 'w')

print("STARTING TESTS...")
import unittest

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

# Run a quick sanity check
try:
    manager = AccountManager(price_provider=lambda s: {"AAPL": 150.0, "TSLA": 250.0, "GOOGL": 140.0}[s])
    acc_id = manager.create_account(0.0)
    assert isinstance(acc_id, str) and len(acc_id) > 0
    assert manager.get_portfolio_value(acc_id) == 0.0
    assert manager.get_transaction_history(acc_id) == []
    print("Sanity test 1 passed: zero deposit")
except Exception as e:
    print(f"Sanity test 1 FAILED: {e}")
    import traceback
    traceback.print_exc()

try:
    loader = unittest.TestLoader()
    suite = loader.loadTestsFromName("test_backend")
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    print(f"Tests run: {result.testsRun}")
    print(f"Errors: {len(result.errors)}")
    print(f"Failures: {len(result.failures)}")
    for test, tb in result.errors:
        print(f"ERROR: {test}")
        print(tb)
    for test, tb in result.failures:
        print(f"FAILURE: {test}")
        print(tb)
    print(f"SUCCESS: {result.wasSuccessful()}")
except Exception as e:
    print(f"Test discovery/run FAILED: {e}")
    import traceback
    traceback.print_exc()

sys.stdout.close()
sys.stderr.close()
