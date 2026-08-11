from share_prices import get_share_price

# Test known symbols
assert get_share_price("AAPL") == 150.00
assert get_share_price("TSLA") == 250.00
assert get_share_price("GOOGL") == 140.00

# Test unknown symbol
try:
    get_share_price("MSFT")
    assert False, "Should have raised ValueError"
except ValueError as e:
    assert str(e) == "Unknown symbol: MSFT"

print("All tests passed!")
