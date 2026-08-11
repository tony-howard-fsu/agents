"""Quick smoke-test for portfolio_manager.py."""
import json

from portfolio_manager import (
    AccountManager,
    TestSharePriceProvider,
    Transaction,
    TransactionType,
    get_default_manager,
    reset_manager,
)


def test_full_flow():
    mgr = AccountManager()
    pp = TestSharePriceProvider()

    # Create account
    acct = mgr.create_account("Test User", initial_deposit=10000.0)
    assert acct.name == "Test User"
    assert acct.balance == 10000.0
    assert acct.total_deposited == 10000.0
    assert acct.total_withdrawn == 0.0
    assert len(acct.transactions) == 1  # initial deposit txn

    # Deposit
    mgr.deposit(acct.account_id, 5000.0)
    acct = mgr.get_account(acct.account_id)
    assert acct.balance == 15000.0

    # Withdraw
    mgr.withdraw(acct.account_id, 2000.0)
    acct = mgr.get_account(acct.account_id)
    assert acct.balance == 13000.0

    # Buy
    mgr.buy(acct.account_id, "AAPL", 10, pp)
    acct = mgr.get_account(acct.account_id)
    assert acct.holdings.get("AAPL") == 10
    assert acct.balance == 13000.0 - (10 * 150.0)

    # Sell
    mgr.sell(acct.account_id, "AAPL", 5, pp)
    acct = mgr.get_account(acct.account_id)
    assert acct.holdings.get("AAPL") == 5

    # Holdings
    h = mgr.get_holdings(acct.account_id)
    assert h == {"AAPL": 5}

    # Portfolio value
    pv = mgr.get_portfolio_value(acct.account_id, pp)
    expected_pv = acct.balance + 5 * 150.0
    assert abs(pv - expected_pv) < 0.01

    # Profit/Loss
    pl = mgr.get_profit_loss(acct.account_id, pp)
    expected_pl = (pv + acct.total_withdrawn) - acct.total_deposited
    assert abs(pl - expected_pl) < 0.01

    # Transaction serialization round-trip
    txn = acct.transactions[0]
    d = txn.to_dict()
    assert d["transaction_type"] == "DEPOSIT"
    restored = Transaction.from_dict(d)
    assert restored.transaction_id == txn.transaction_id
    assert restored.transaction_type == TransactionType.DEPOSIT
    assert restored.amount == txn.amount

    # Account serialization
    ad = acct.to_dict()
    assert ad["name"] == "Test User"
    ra = type(acct).from_dict(ad)
    assert ra.name == "Test User"

    # Error handling
    try:
        mgr.create_account("", 0)
        assert False, "Should have raised"
    except ValueError:
        pass

    try:
        mgr.get_account("nonexistent")
        assert False, "Should have raised"
    except KeyError:
        pass

    try:
        mgr.withdraw(acct.account_id, 99999999)
        assert False, "Should have raised"
    except ValueError:
        pass

    try:
        mgr.buy(acct.account_id, "AAPL", 999999, pp)
        assert False, "Should have raised"
    except ValueError:
        pass

    try:
        mgr.sell(acct.account_id, "AAPL", 999999, pp)
        assert False, "Should have raised"
    except ValueError:
        pass

    try:
        pp.get_share_price("UNKNOWN")
        assert False, "Should have raised"
    except ValueError:
        pass

    # Module-level convenience
    reset_manager()
    dm = get_default_manager()
    assert dm is not None
    dm2 = get_default_manager()
    assert dm is dm2
    reset_manager()
    dm3 = get_default_manager()
    assert dm3 is not dm

    print("All smoke tests passed!")


if __name__ == "__main__":
    test_full_flow()
