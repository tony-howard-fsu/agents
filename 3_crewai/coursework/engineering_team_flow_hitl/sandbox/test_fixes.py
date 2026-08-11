"""Smoke-test the three fixes in backend.py."""
from backend import AccountManager, SharePriceService, Transaction

# --- Fix 3: AccountManager.__init__ accepts optional price_service ---
custom_ps = SharePriceService()
mgr1 = AccountManager()                # default price service
mgr2 = AccountManager(price_service=custom_ps)  # injected
assert mgr1._price_service is not mgr2._price_service
print("PASS: AccountManager.__init__ accepts optional price_service.")

# --- Fix 2: create_account with initial_deposit > 0 creates DEPOSIT tx ---
acct_id = mgr1.create_account("Test", 100.0)
txns = mgr1.get_transactions(acct_id)
assert len(txns) == 1, f"Expected 1 transaction, got {len(txns)}"
tx = txns[0]
assert tx.type == "DEPOSIT"
assert tx.amount == 100.0
print("PASS: create_account with deposit creates initial DEPOSIT transaction.")

# Also test with 0 deposit (should NOT create a DEPOSIT transaction)
acct2 = mgr1.create_account("ZeroDep", 0.0)
txns2 = mgr1.get_transactions(acct2)
assert len(txns2) == 0, f"Expected 0 transactions for zero deposit, got {len(txns2)}"
print("PASS: create_account with 0 deposit does NOT create a transaction.")

# --- Fix 1: list_accounts() returns list[dict] with id and name keys ---
accounts = mgr1.list_accounts()
assert isinstance(accounts, list)
assert all(isinstance(a, dict) for a in accounts)
assert all("id" in a and "name" in a for a in accounts)
# Verify it contains our accounts
ids = {a["id"] for a in accounts}
assert acct_id in ids
assert acct2 in ids
print("PASS: list_accounts() returns list[dict] with 'id' and 'name' keys.")

print("\nAll three fixes verified successfully!")
