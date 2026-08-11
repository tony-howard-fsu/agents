# Account Management System Design

## 1. Overview
The system manages multiple user accounts for a trading simulation platform. It supports creating accounts, depositing/withdrawing cash, recording stock trades (buy/sell), and generating reports: portfolio valuation, profit/loss, holdings, and transaction history. All real-time share prices are obtained via an injected function `get_share_price(symbol)`. The system runs in‑memory and exposes a clean API for a Gradio frontend.

---

## 2. Modules & Files
All files reside in the same project root.

| File | Responsibility |
|------|----------------|
| `backend.py` | Core account management logic (Account and AccountManager classes, data structures, custom exceptions). |
| `share_prices.py` | Test implementation of `get_share_price`. |
| `app.py` | Gradio web interface using the backend API (built by frontend engineer). |

---

## 3. Data Structures

### 3.1 `Transaction` (dataclass)
Represents a single financial event.

```python
from dataclasses import dataclass, field
from datetime import datetime

@dataclass
class Transaction:
    type: str               # "DEPOSIT", "WITHDRAW", "BUY", "SELL"
    symbol: str = ""        # Stock symbol; empty for cash transactions
    quantity: float = 0.0   # Number of shares; 0 for cash transactions
    price: float = 0.0      # Price per share; 0 for cash transactions
    amount: float = 0.0     # Cash amount for deposit/withdraw; for trades, amount = quantity * price (also stored)
    timestamp: datetime = field(default_factory=datetime.now)
```

### 3.2 `Holding` (dataclass)
A snapshot of a stock position.

```python
@dataclass
class Holding:
    symbol: str
    quantity: float
```

### 3.3 Account State
Each account maintains:
- `cash_balance: float`
- `holdings: Dict[str, float]`   (symbol → quantity)
- `initial_deposit: float`       (set once at creation)
- `transactions: List[Transaction]`  (append‑only log)

---

## 4. Custom Exceptions
```python
class InsufficientFundsError(Exception): ...
class InsufficientSharesError(Exception): ...
```

---

## 5. Price Provider
The share‑price function is **injected** to allow test doubles.

**Test implementation** (`share_prices.py`):
```python
def get_share_price(symbol: str) -> float:
    """Returns fixed test prices for AAPL, TSLA, GOOGL."""
    # Raises ValueError for unknown symbols
```

The signature expected by the backend is `Callable[[str], float]`.

---

## 6. Backend API

### 6.1 `AccountManager` class (`backend.py`)

#### Constructor
```python
def __init__(self, price_provider: Callable[[str], float] = get_share_price):
    """
    Args:
        price_provider: function to fetch current share prices.
                        Default to test implementation if not provided.
    """
```
- Stores `self._accounts: Dict[str, Account]` (keyed by account ID).
- Stores the `price_provider`.

#### Public Methods

**Account lifecycle & cash operations**
```python
def create_account(self, initial_deposit: float = 0.0) -> str:
    """Creates a new account with an optional initial deposit.
       Raises ValueError if deposit is negative.
       Returns unique account ID (UUID string).
    """

def deposit(self, account_id: str, amount: float) -> None:
    """Adds cash to account. amount > 0 required."""

def withdraw(self, account_id: str, amount: float) -> None:
    """Removes cash, raising InsufficientFundsError if amount > cash_balance.
       amount > 0 required.
    """
```

**Trade recording**
```python
def record_trade(self, account_id: str, trade_type: str, symbol: str, quantity: float) -> None:
    """Records a BUY or SELL trade.
       - Uses self.price_provider(symbol) for current price.
       - Validates:
           * BUY:  (quantity * price) <= cash_balance  → else InsufficientFundsError
           * SELL: quantity <= current holding quantity → else InsufficientSharesError
       - Updates cash, holdings, and transaction log.
    """
```

**Reporting**
```python
def get_portfolio_value(self, account_id: str) -> float:
    """Returns cash + sum(holding.quantity * current price) for all holdings."""

def get_profit_loss(self, account_id: str) -> float:
    """Returns portfolio_value - initial_deposit."""

def get_holdings_report(self, account_id: str) -> List[Holding]:
    """Returns list of Holding objects for non‑zero quantities."""

def get_pnl_report(self, account_id: str) -> float:
    """Alias for get_profit_loss, provides a clear reporting entry point."""

def get_transaction_history(self, account_id: str) -> List[Transaction]:
    """Returns the full chronological list of transactions."""
```

---

### 6.2 Internal `Account` Class (private to backend)
```python
class Account:
    def __init__(self, account_id: str, initial_deposit: float):
        # initialises cash, holdings, transactions, etc.
```

All validation and state modifications happen inside `Account` methods, called by `AccountManager` after looking up the account.

---

## 7. Validation Enforcement Points
| Rule | Where checked | Exception |
|------|--------------|-----------|
| Withdraw more than cash | `Account.withdraw()` | `InsufficientFundsError` |
| Buy with insufficient cash | `Account.buy(symbol, quantity, price)` | `InsufficientFundsError` |
| Sell shares not owned | `Account.sell(symbol, quantity)` | `InsufficientSharesError` |
| Deposit/withdraw negative amounts | `Account.deposit/withdraw` | `ValueError` |
| Unknown symbol on trade | `price_provider` call | `ValueError` (from price provider) |

---

## 8. Dependency Injection for Testability
- The `get_share_price` function is passed to `AccountManager` constructor.
- Test engineer can supply a `MagicMock` or a custom function to control prices.
- The default is the test implementation from `share_prices.py`.
- All public methods of `AccountManager` are testable in isolation.

---

## 9. Public API for the Gradio Frontend
The frontend (`app.py`) will instantiate one `AccountManager(price_provider=...)` globally (or inside a class) and call these methods:

- `manager.create_account(initial_deposit) -> account_id`
- `manager.deposit(account_id, amount)`
- `manager.withdraw(account_id, amount)`
- `manager.record_trade(account_id, "BUY", symbol, qty)` / `"SELL"`
- `manager.get_portfolio_value(account_id) -> float`
- `manager.get_profit_loss(account_id) -> float`
- `manager.get_holdings_report(account_id) -> list[Holding]`
- `manager.get_transaction_history(account_id) -> list[Transaction]`

All methods that return data structures should return simple Python objects (`float`, `list`s of `Holding`/`Transaction`) that Gradio can display.

---

## 10. Gradio 6 UI Guidance for Frontend Engineer
**Important Gradio 6 changes:**
- **No `gr.update()`:** Functions must return the new value for output components directly.
- **Component references:** Use `.value` to get/set values only inside event functions; do not assign `.value` outside.
- **Event wiring:** `component.event(fn=..., inputs=[...], outputs=[...])`
- **Data display:** Use `gr.Dataframe(headers=[...], values=[[...]])` to show tables. Return a list of rows (each row a list) or a pandas DataFrame for `gr.Dataframe`.
- **Containers:** `gr.Row()`, `gr.Column()` for layout.
- **State:** Use `gr.State()` to hold the `account_id` across function calls.

**Suggested app structure:**
1. Use `gr.Blocks()` as the main context.
2. Keep the `AccountManager` instance as a module-level variable, not inside Gradio state.
3. Provide:
   - An **account creation** section: textbox for initial deposit, a "Create" button. Output: display generated `account_id`. Store `account_id` in a `gr.State()`.
   - A **cash operations** section: number inputs for amount, buttons for Deposit/Withdraw. Use account ID from state.
   - A **trade** section: textbox for symbol, number for quantity, radio or dropdown for BUY/SELL, a "Submit" button.
   - **Report buttons**: "Portfolio Value", "Profit/Loss", "Holdings", "Transaction History". Output each as a `gr.Textbox` or `gr.Dataframe` as appropriate.
4. For reports that return lists (holdings, transactions), convert them to a format suitable for `gr.Dataframe`:
   - Holdings: `[[h.symbol, h.quantity] for h in holdings]` with headers `["Symbol", "Quantity"]`.
   - Transactions: `[[t.timestamp.isoformat(), t.type, t.symbol, t.quantity, t.price, t.amount] for t in txs]` with headers `["Timestamp", "Type", "Symbol", "Quantity", "Price", "Amount"]`.
5. Use `gr.Dataframe` `headers` and `values` arguments (values can be a list of lists). For dynamic updates, the event function returns the updated `values` list.
6. Error handling: Wrap backend calls in try/except and return error messages to a `gr.Textbox` status display.

---

## 11. Testing Considerations (for Test Engineer)
- All public `AccountManager` methods are targets.
- Exception scenarios: insufficient funds, insufficient shares, negative amounts, unknown symbols.
- The `price_provider` can be replaced with a mock to control price responses.
- Edge cases: zero deposit, zero‑quantity trades, multiple accounts, concurrent operations (if required later).
- Test coverage: each method with valid and invalid inputs, transaction log integrity, holdings accuracy, P&L calculation with different price movements, portfolio valuation with partial and full sell‑offs.

---

## 12. Design Decisions Summary
- **Single `AccountManager` + multiple `Account` objects**: clean separation of concerns, easy to extend to persistent storage later.
- **Transaction log append‑only**: ensures auditability, supports historical reports.
- **Holdings as a simple `dict[symbol] -> quantity`**: sufficient for current reporting and validation.
- **Profit/Loss definition**: `portfolio_value - initial_deposit` where `initial_deposit` is set at account creation and never changes. This matches the literal requirement; additional deposits/withdrawals affect cash but not the baseline. (If a different interpretation is desired, only the `get_profit_loss` method needs adjustment.)
- **Price injection**: constructor dependency enables seamless testing and real‑time price source swapping in the future.