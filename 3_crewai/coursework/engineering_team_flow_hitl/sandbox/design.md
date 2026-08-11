# Detailed Design: Trading Simulation Account Management System

---

## 1. Overview

This document lays out the complete module structure, class hierarchy, function signatures, and UI component layout for the account management system. The system is split across three files:

| File | Owner | Purpose |
|------|-------|---------|
| `backend.py` | Backend Engineer | Core domain logic, state management, price service |
| `app.py` | Frontend Engineer | Gradio-based responsive UI with dark mode |
| `test_backend.py` | Test Engineer | Unit tests covering all backend functionality |

All files reside in a single flat directory inside a `uv` project with `gradio` installed.

---

## 2. Backend Module (`backend.py`)

### 2.1 Imports

```
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional
```

### 2.2 `Transaction` — Immutable Dataclass

Represents a single financial event in the account lifecycle.

```
@dataclass(frozen=True)
class Transaction:
    id: str
    type: str                  # "DEPOSIT" | "WITHDRAW" | "BUY" | "SELL"
    symbol: Optional[str]      # None for DEPOSIT/WITHDRAW; ticker for BUY/SELL
    quantity: Optional[int]    # None for DEPOSIT/WITHDRAW
    price: Optional[float]     # None for DEPOSIT/WITHDRAW; per-share price for BUY/SELL
    amount: float              # cash impact: positive = inflow, negative = outflow
    timestamp: datetime
    account_id: str
```

- `amount` is the **cash change**: deposits are positive, withdrawals are negative, buy costs are negative, sell proceeds are positive.
- The `id` is a UUID4 string generated at creation time.

### 2.3 `Holding` — Immutable Dataclass

Represents a snapshot of the user's position in a single symbol.

```
@dataclass(frozen=True)
class Holding:
    symbol: str
    quantity: int
    avg_cost_per_share: float
```

### 2.4 `SharePriceService` — Price Lookup

Encapsulates share price retrieval. Test implementation returns fixed prices.

```
class SharePriceService:
    # Map of symbol -> fixed price for test implementation
    _TEST_PRICES: dict[str, float]     # class-level: {"AAPL": 150.0, "TSLA": 250.0, "GOOGL": 175.0}

    def get_share_price(self, symbol: str) -> float:
        """
        Returns current price for `symbol`.
        Raises ValueError if symbol is unknown.
        """
```

### 2.5 `_Account` — Internal Mutable State Class

**Not exposed outside `backend.py`.** Holds all state for a single account. `AccountManager` is the only code that touches it.

```
class _Account:
    def __init__(self, account_id: str, name: str, initial_deposit: float) -> None:
        self.id: str = account_id
        self.name: str = name
        self.balance: float = initial_deposit
        self.holdings: dict[str, Holding] = {}          # symbol -> Holding
        self.transactions: list[Transaction] = []
        self.initial_deposit: float = initial_deposit
        self.total_deposited: float = initial_deposit
        self.total_withdrawn: float = 0.0
```

Internal mutating methods (called only by `AccountManager` after validation):

```
    def _add_transaction(self, tx: Transaction) -> None:
        """Append transaction to history."""

    def _apply_deposit(self, amount: float, tx: Transaction) -> None:
        """balance += amount; total_deposited += amount; store tx."""

    def _apply_withdraw(self, amount: float, tx: Transaction) -> None:
        """balance -= amount; total_withdrawn += amount; store tx."""

    def _apply_buy(self, symbol: str, quantity: int, price: float, tx: Transaction) -> None:
        """
        Deduct cost from balance. Update or create Holding with new
        average cost per share: new_avg = (old_qty*old_avg + quantity*price) / (old_qty + quantity).
        Store tx.
        """

    def _apply_sell(self, symbol: str, quantity: int, price: float, tx: Transaction) -> None:
        """
        Add proceeds to balance. Reduce Holding quantity.
        If quantity reaches zero, remove the Holding entry.
        avg_cost_per_share remains unchanged (cost basis preserved).
        Store tx.
        """

    def _can_withdraw(self, amount: float) -> bool:
        """True if balance >= amount."""

    def _can_buy(self, symbol: str, quantity: int, price: float) -> bool:
        """True if balance >= quantity * price."""

    def _can_sell(self, symbol: str, quantity: int) -> bool:
        """True if symbol in holdings and holding.quantity >= quantity."""

    def _get_portfolio_value(self, current_prices: dict[str, float]) -> float:
        """cash balance + sum(holding.qty * current_prices[symbol] for each holding)."""

    def _get_profit_loss(self, current_prices: dict[str, float]) -> float:
        """
        (balance + market_value_of_holdings) - (total_deposited - total_withdrawn)
        Equivalently: portfolio_value - net_cash_invested.
        """

    def _get_holdings_snapshot(self) -> list[Holding]:
        """Return a copy of all Holding objects."""

    def _get_transactions_snapshot(self) -> list[Transaction]:
        """Return a copy of the transaction list."""

    def _get_balance(self) -> float:
        """Return current cash balance."""
```

### 2.6 `AccountManager` — Public API (Single Entry Point)

This is the **only class imported by the frontend**. It coordinates accounts and the price service.

```
class AccountManager:
    def __init__(self, price_service: Optional[SharePriceService] = None) -> None:
        """
        If price_service is None, create a default SharePriceService.
        Initializes empty accounts dict.
        """

    # --- Account lifecycle ---

    def create_account(self, name: str, initial_deposit: float = 0.0) -> str:
        """
        Creates a new _Account. Returns the new account_id (UUID4 string).
        initial_deposit must be >= 0. Creates initial DEPOSIT transaction.
        Raises ValueError if initial_deposit < 0 or name is empty.
        """

    def get_account_name(self, account_id: str) -> str:
        """Returns the account name. Raises KeyError if not found."""

    def list_accounts(self) -> list[dict]:
        """
        Returns [{"id": ..., "name": ...}, ...] for all accounts.
        """

    # --- Cash operations ---

    def deposit(self, account_id: str, amount: float) -> Transaction:
        """
        Adds cash to account. amount must be > 0.
        Returns the created Transaction.
        Raises ValueError if amount <= 0; KeyError if account missing.
        """

    def withdraw(self, account_id: str, amount: float) -> Transaction:
        """
        Removes cash from account. amount must be > 0 and <= balance.
        Returns the created Transaction.
        Raises ValueError if amount <= 0, or if insufficient balance; KeyError if account missing.
        """

    # --- Trading operations ---

    def buy(self, account_id: str, symbol: str, quantity: int) -> Transaction:
        """
        Buys `quantity` shares of `symbol`.
        Fetches price from self._price_service.get_share_price(symbol).
        Validates: quantity > 0, symbol valid, sufficient balance.
        Returns the created Transaction.
        Raises ValueError if validation fails; KeyError if account missing.
        """

    def sell(self, account_id: str, symbol: str, quantity: int) -> Transaction:
        """
        Sells `quantity` shares of `symbol`.
        Fetches price from self._price_service.get_share_price(symbol).
        Validates: quantity > 0, symbol valid, sufficient holdings.
        Returns the created Transaction.
        Raises ValueError if validation fails; KeyError if account missing.
        """

    # --- Queries (read-only, return copies) ---

    def get_balance(self, account_id: str) -> float:
        """Return current cash balance."""

    def get_holdings(self, account_id: str) -> list[Holding]:
        """Return list of Holding snapshots."""

    def get_portfolio_value(self, account_id: str) -> float:
        """Return balance + market value of all holdings using current prices."""

    def get_profit_loss(self, account_id: str) -> float:
        """Return portfolio_value - net_cash_invested."""

    def get_transactions(self, account_id: str) -> list[Transaction]:
        """Return list of all Transaction snapshots, most recent first."""

    def get_holdings_with_market_value(self, account_id: str) -> list[dict]:
        """
        Return list of dicts:
        {"symbol": str, "quantity": int, "avg_cost": float, "current_price": float, "market_value": float, "unrealized_pl": float}
        Useful for frontend display.
        """
```

### 2.7 Internal Validation Rules Summary

| Operation | Checks | Error on Failure |
|-----------|--------|------------------|
| `create_account` | `name` non-empty string; `initial_deposit >= 0` | `ValueError` |
| `deposit` | `amount > 0` | `ValueError` |
| `withdraw` | `amount > 0`; `balance >= amount` | `ValueError` |
| `buy` | `quantity > 0` (int); symbol known; `balance >= quantity * price` | `ValueError` |
| `sell` | `quantity > 0` (int); symbol known; holding exists with `qty >= quantity` | `ValueError` |
| Any operation | `account_id` exists | `KeyError` |

---

## 3. Frontend Module (`app.py`)

### 3.1 Technology & Styling

- **Framework**: Gradio (using `gr.Blocks`)
- **Theme**: `gr.themes.Soft()` or a custom dark-mode theme via `gr.themes.Base` with dark color palette
- **Layout**: Responsive, uses `gr.Row`, `gr.Column`, `gr.Tabs`, `gr.Tab`, `gr.Group`
- **Icons**: Emoji or Unicode characters for visual cues
- **All data scrollable**: Use `gr.DataFrame` with `max_height` or wrap in scrollable containers

### 3.2 Global State

A `gr.State` object holds the `AccountManager` instance (instantiated once at app startup).

### 3.3 UI Structure (Top to Bottom)

```
┌──────────────────────────────────────────────────────┐
│  Tabs (top-level)                                    │
│  ┌──────────────┬──────────────────────────────┐     │
│  │ 📋 Profile   │ ➕ Create Account             │     │
│  └──────────────┴──────────────────────────────┘     │
│                                                      │
│  [Profile Tab active]                                │
│  ┌──────────────────────────────────────────────┐    │
│  │ Account: [Dropdown: account_id → name]       │    │
│  │ [Select Account]  [Refresh]                  │    │
│  └──────────────────────────────────────────────┘    │
│                                                      │
│  [When account selected — sub-tabs appear:]          │
│  ┌──────────────────────────────────────────────┐    │
│  │ 💵 Deposit │ 🏦 Withdraw │ 📈 Trade │        │    │
│  │ 📊 Holdings │ 💰 P&L │ 🧾 Transactions       │    │
│  └──────────────────────────────────────────────┘    │
│                                                      │
│  [Contents of active sub-tab rendered below]         │
└──────────────────────────────────────────────────────┘
```

### 3.4 Component Details

#### 3.4.1 Top-Level Tabs

```
with gr.Blocks(theme=gr.themes.Soft(), title="Trading Simulator") as demo:
    account_manager_state = gr.State(value=AccountManager())

    with gr.Tabs() as top_tabs:
        with gr.Tab("📋 Profile", id="profile_tab"):
            # ... all profile content ...
        with gr.Tab("➕ Create Account", id="create_tab"):
            # ... account creation form ...
```

#### 3.4.2 "Create Account" Tab

| Component | Type | Properties |
|-----------|------|------------|
| Account Name | `gr.Textbox` | `label="Account Name"`, `placeholder="Enter name..."` |
| Initial Deposit | `gr.Number` | `label="Initial Deposit ($)"`, `value=0.0`, `minimum=0.0` |
| Create Button | `gr.Button` | `value="Create Account"`, `variant="primary"` |
| Status Message | `gr.Markdown` | Initially hidden/shows success or error |

Event flow:
- Button click → calls `handle_create_account(name, initial_deposit, manager)` → returns updated account dropdown choices + status message.

#### 3.4.3 "Profile" Tab

**Upper area — Account Selector:**

| Component | Type | Properties |
|-----------|------|------------|
| Account Dropdown | `gr.Dropdown` | `label="Select Account"`, `choices=[]`, `interactive=True` |
| Select Button | `gr.Button` | `value="Load Account"`, `variant="primary"` |
| Account Info | `gr.Markdown` | Displays "Account: {name} | Balance: ${balance}" |

Initially, if no accounts exist, the dropdown is empty and a message says "No accounts yet — go to Create Account tab."

**Lower area — Sub-Tabs (visible only after account loaded):**

```
with gr.Tabs(visible=False) as sub_tabs:
    with gr.Tab("💵 Deposit"):
        deposit_amount = gr.Number(label="Amount ($)", minimum=0.01)
        deposit_btn = gr.Button("Deposit", variant="primary")
        deposit_status = gr.Markdown(visible=False)

    with gr.Tab("🏦 Withdraw"):
        withdraw_amount = gr.Number(label="Amount ($)", minimum=0.01)
        withdraw_btn = gr.Button("Withdraw", variant="stop")
        withdraw_status = gr.Markdown(visible=False)

    with gr.Tab("📈 Trade"):
        with gr.Row():
            with gr.Column(scale=1):
                trade_symbol = gr.Dropdown(
                    label="Symbol", choices=["AAPL", "TSLA", "GOOGL"]
                )
                trade_quantity = gr.Number(label="Quantity", minimum=1, precision=0)
                current_price_display = gr.Number(label="Current Price ($)", interactive=False)
            with gr.Column(scale=1):
                trade_total = gr.Number(label="Estimated Total ($)", interactive=False)
                buy_btn = gr.Button("Buy", variant="primary")
                sell_btn = gr.Button("Sell", variant="stop")
        trade_status = gr.Markdown(visible=False)

    with gr.Tab("📊 Holdings"):
        holdings_table = gr.DataFrame(
            headers=["Symbol", "Quantity", "Avg Cost", "Current Price", "Market Value", "Unrealized P/L"],
            interactive=False,
            max_height=300
        )

    with gr.Tab("💰 P&L"):
        pl_display = gr.Markdown()

    with gr.Tab("🧾 Transactions"):
        transactions_table = gr.DataFrame(
            headers=["Time", "Type", "Symbol", "Quantity", "Price", "Amount"],
            interactive=False,
            max_height=300
        )
```

#### 3.4.4 Event Handlers (Function Signatures)

```
def handle_create_account(
    name: str,
    initial_deposit: float,
    manager: AccountManager
) -> tuple[str, list[list[str, str]], str]:
    """
    Returns (status_message, updated_choices, account_id_for_dropdown_select).
    If error: status_message = error text, choices unchanged.
    """

def handle_select_account(
    account_id: str,
    manager: AccountManager
) -> tuple[str, bool, list, list, str, list]:
    """
    Returns (
        account_info_markdown,
        sub_tabs_visible,
        holdings_data,
        transactions_data,
        pl_markdown,
        updated_trade_dropdown_choices
    ).
    Also clears previous data if account_id is None.
    """

def handle_deposit(
    account_id: str,
    amount: float,
    manager: AccountManager
) -> tuple[str, str, list, list, str]:
    """
    Returns (status, updated_info_md, updated_holdings, updated_transactions, updated_pl).
    """

def handle_withdraw(
    account_id: str,
    amount: float,
    manager: AccountManager
) -> tuple[str, str, list, list, str]:
    """
    Returns (status, updated_info_md, updated_holdings, updated_transactions, updated_pl).
    """

def handle_trade_symbol_change(
    symbol: str,
    manager: AccountManager
) -> tuple[float, float]:
    """
    When trade symbol dropdown changes, fetch price and return (price, 0.0).
    """

def handle_trade_quantity_change(
    quantity: int,
    price: float
) -> float:
    """
    When quantity changes, return quantity * price as estimated total.
    """

def handle_buy(
    account_id: str,
    symbol: str,
    quantity: int,
    manager: AccountManager
) -> tuple[str, str, list, list, str]:
    """
    Execute buy. Returns (status, updated_info_md, updated_holdings, updated_transactions, updated_pl).
    """

def handle_sell(
    account_id: str,
    symbol: str,
    quantity: int,
    manager: AccountManager
) -> tuple[str, str, list, list, str]:
    """
    Execute sell. Returns (status, updated_info_md, updated_holdings, updated_transactions, updated_pl).
    """

def refresh_profile_data(
    account_id: str,
    manager: AccountManager
) -> tuple[str, list, list, str]:
    """
    Refreshes info_md, holdings, transactions, pl without performing any action.
    Called after every successful operation to keep UI current.
    """
```

### 3.5 Data Clearing on Account Switch

When the user selects a different account from the dropdown, all previous data (holdings table, transactions table, P&L, status messages) is cleared and repopulated with the newly selected account's data.

### 3.6 Responsive & Visual Design Notes

- Use `gr.Column(scale=...)` and `gr.Row(scale=...)` for proportional layout.
- All `gr.DataFrame` components use `max_height=300` with vertical scroll.
- Dark mode: use `gr.themes.Soft(spacing_size="lg", font=[gr.themes.GoogleFont("Inter")])` or a custom theme preset.
- Success status messages in green, errors in red (via Markdown with HTML/CSS).
- Buttons use `variant="primary"` for confirmatory actions (deposit, buy), `variant="stop"` for destructive/reversible actions (withdraw, sell).
- The current price field updates reactively when the symbol dropdown changes (no button required).

---

## 4. Test Module (`test_backend.py`)

### 4.1 Test Structure

```
import pytest
from backend import AccountManager, SharePriceService, Transaction, Holding

class TestSharePriceService:
    def test_get_known_price(self) -> None: ...
    def test_get_unknown_price_raises(self) -> None: ...

class TestAccountCreation:
    def test_create_account_with_initial_deposit(self) -> None: ...
    def test_create_account_zero_deposit(self) -> None: ...
    def test_create_account_negative_deposit_raises(self) -> None: ...
    def test_create_account_empty_name_raises(self) -> None: ...
    def test_create_account_returns_unique_ids(self) -> None: ...

class TestDeposit:
    def test_deposit_increases_balance(self) -> None: ...
    def test_deposit_negative_amount_raises(self) -> None: ...
    def test_deposit_zero_amount_raises(self) -> None: ...
    def test_deposit_to_nonexistent_account_raises(self) -> None: ...
    def test_deposit_creates_transaction(self) -> None: ...

class TestWithdraw:
    def test_withdraw_decreases_balance(self) -> None: ...
    def test_withdraw_insufficient_funds_raises(self) -> None: ...
    def test_withdraw_negative_amount_raises(self) -> None: ...
    def test_withdraw_zero_amount_raises(self) -> None: ...
    def test_withdraw_exact_balance_succeeds(self) -> None: ...

class TestBuy:
    def test_buy_creates_holding(self) -> None: ...
    def test_buy_insufficient_funds_raises(self) -> None: ...
    def test_buy_unknown_symbol_raises(self) -> None: ...
    def test_buy_zero_quantity_raises(self) -> None: ...
    def test_buy_negative_quantity_raises(self) -> None: ...
    def test_buy_updates_average_cost(self) -> None: ...
    def test_buy_multiple_lots_correct_avg_cost(self) -> None: ...

class TestSell:
    def test_sell_reduces_holding(self) -> None: ...
    def test_sell_all_shares_removes_holding(self) -> None: ...
    def test_sell_more_than_owned_raises(self) -> None: ...
    def test_sell_symbol_not_owned_raises(self) -> None: ...
    def test_sell_zero_quantity_raises(self) -> None: ...
    def test_sell_negative_quantity_raises(self) -> None: ...
    def test_sell_increases_balance(self) -> None: ...

class TestPortfolioValue:
    def test_portfolio_value_cash_only(self) -> None: ...
    def test_portfolio_value_with_holdings(self) -> None: ...
    def test_portfolio_value_after_buy_and_price_change(self) -> None: ...

class TestProfitLoss:
    def test_profit_loss_zero_initial(self) -> None: ...
    def test_profit_loss_with_gains(self) -> None: ...
    def test_profit_loss_with_losses(self) -> None: ...
    def test_profit_loss_after_multiple_deposits(self) -> None: ...
    def test_profit_loss_after_deposit_and_withdraw(self) -> None: ...

class TestHoldings:
    def test_holdings_empty_initially(self) -> None: ...
    def test_holdings_returns_copy_not_reference(self) -> None: ...
    def test_get_holdings_with_market_value(self) -> None: ...

class TestTransactions:
    def test_transactions_empty_initially(self) -> None: ...
    def test_transactions_recorded_in_order(self) -> None: ...
    def test_transactions_return_copy(self) -> None: ...
    def test_transaction_types_are_correct(self) -> None: ...

class TestListAccounts:
    def test_list_accounts_empty(self) -> None: ...
    def test_list_accounts_after_creation(self) -> None: ...

class TestGetAccountName:
    def test_get_account_name_valid(self) -> None: ...
    def test_get_account_name_invalid_raises(self) -> None: ...

class TestDataClearing:
    """Edge case: ensure accounts are independent."""
    def test_accounts_do_not_share_state(self) -> None: ...
```

### 4.2 Key Test Fixtures

```
@pytest.fixture
def price_service() -> SharePriceService: ...

@pytest.fixture
def manager(price_service) -> AccountManager: ...

@pytest.fixture
def account_id(manager) -> str:
    """Creates an account with $10,000 initial deposit."""
```

### 4.3 Edge Cases to Cover

1. Withdrawing the exact balance → balance becomes 0, succeeds.
2. Buying with exact cash available → balance becomes 0, succeeds.
3. Selling all shares → holding entry removed entirely.
4. Multiple buys of the same symbol at different prices → average cost per share correctly recomputed.
5. Unknown symbol in buy/sell → `ValueError` propagated from `SharePriceService`.
6. P&L calculation after deposits, withdrawals, buys, sells, and price changes.
7. Immutable return values: modifying a returned list does not affect internal state.
8. Account isolation: operations on account A do not affect account B.
9. Transaction history order and completeness.
10. `create_account` with empty or whitespace-only name.

---

## 5. File Summary

```
project/
├── pyproject.toml          # uv project config, depends on gradio, pytest
├── backend.py              # All backend classes (AccountManager, SharePriceService, Transaction, Holding, _Account)
├── app.py                  # Gradio UI (imports AccountManager from backend)
└── test_backend.py         # pytest unit tests (imports from backend)
```

---

## 6. Data Flow Diagram

```
┌──────────────┐     calls      ┌─────────────────┐     mutates      ┌────────────┐
│   app.py     │ ──────────────→ │  AccountManager │ ───────────────→ │  _Account  │
│  (Gradio UI) │ ←────────────── │  (public API)   │ ←─────────────── │  (state)   │
└──────────────┘   returns       └────────┬────────┘    queries       └────────────┘
       │                copies            │
       │                                  │ calls
       │                           ┌──────┴──────────┐
       │                           │ SharePriceService│
       │                           │  (fixed prices)  │
       │                           └─────────────────┘
       │
       ▼
  User sees: balance, holdings, P&L, transactions
```

- `app.py` never imports `_Account`. It only interacts with `AccountManager`.
- `AccountManager` is the sole mediator between UI and state.
- All prices are fetched at the moment of a `buy`/`sell`/`get_portfolio_value`/`get_profit_loss` call, ensuring consistency.

---

## 7. Acceptance Criteria Checklist

| # | Requirement | Covered By |
|---|-------------|------------|
| 1 | Create an account | `AccountManager.create_account()` |
| 2 | Deposit funds | `AccountManager.deposit()` |
| 3 | Withdraw funds | `AccountManager.withdraw()` |
| 4 | Record buy/sell with quantity | `AccountManager.buy()` / `.sell()` |
| 5 | Calculate total portfolio value | `AccountManager.get_portfolio_value()` |
| 6 | Calculate profit/loss from initial deposit | `AccountManager.get_profit_loss()` |
| 7 | Report holdings at any time | `AccountManager.get_holdings()` / `get_holdings_with_market_value()` |
| 8 | Report P&L at any time | `AccountManager.get_profit_loss()` |
| 9 | List transactions over time | `AccountManager.get_transactions()` |
| 10 | Prevent negative balance on withdraw | Validation in `withdraw()` |
| 11 | Prevent buying more than affordable | Validation in `buy()` |
| 12 | Prevent selling unowned shares | Validation in `sell()` |
| 13 | `get_share_price(symbol)` with fixed prices | `SharePriceService` |
| 14 | Always-visible create-account area | Top-level "Create Account" tab |
| 15 | No other menus if no account | Sub-tabs hidden until account selected |
| 16 | Deposit/withdraw as same-level tabs | Sub-tabs under Profile |
| 17 | Create new account always available as separate tab | Top-level tab alongside Profile |
| 18 | Profile tab with account selector at top, sub-tabs below | Profile tab layout |
| 19 | All data visible, scrollable if needed | `max_height` on DataFrames |
| 20 | Responsive, modern, dark mode, icons | Gradio theme + emoji icons |
| 21 | Data cleared when switching accounts | `handle_select_account` clears and repopulates |
| 22 | Backend in Python | `backend.py` |
| 23 | Gradio app | `app.py` |
| 24 | Unit tests | `test_backend.py` |
| 25 | Single flat directory, uv project | File structure |