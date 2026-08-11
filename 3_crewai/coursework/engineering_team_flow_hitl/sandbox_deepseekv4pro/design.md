# Detailed Design: Trading Simulation Account Management System

---

## 1. Overview

This document provides a detailed technical design for a simple account management system for a trading simulation platform. The system is composed of three components:

- **Backend Module** (`portfolio_manager.py`) – core business logic, written in Python
- **Frontend Module** (`app.py`) – Gradio-based UI
- **Test Module** (`test_portfolio_manager.py`) – unit tests for the backend

All components reside in a single sandbox directory within a `uv` project with `gradio` installed.

---

## 2. Backend Module (`portfolio_manager.py`)

### 2.1. Enumerations

```
class TransactionType(Enum):
    DEPOSIT = "deposit"
    WITHDRAW = "withdraw"
    BUY = "buy"
    SELL = "sell"
```

---

### 2.2. Data Classes

#### 2.2.1. `Transaction` (dataclass)

Represents a single financial transaction.

| Field | Type | Description |
|---|---|---|
| `transaction_id` | `str` | Unique identifier (UUID) |
| `transaction_type` | `TransactionType` | DEPOSIT, WITHDRAW, BUY, or SELL |
| `symbol` | `Optional[str]` | Ticker symbol (only for BUY/SELL) |
| `quantity` | `Optional[int]` | Number of shares (only for BUY/SELL) |
| `price_per_share` | `Optional[float]` | Price at time of trade (only for BUY/SELL) |
| `amount` | `float` | Cash amount (for DEPOSIT/WITHDRAW) or total trade value (quantity * price_per_share) |
| `timestamp` | `datetime` | When the transaction occurred |
| `account_id` | `str` | Owning account ID |

Method signatures:

```
def to_dict() -> dict:
    """Serialize transaction to a dictionary for UI consumption."""

@staticmethod
def from_dict(data: dict) -> Transaction:
    """Deserialize a dictionary back to a Transaction."""
```

---

#### 2.2.2. `Account` (dataclass)

Represents a user account.

| Field | Type | Description |
|---|---|---|
| `account_id` | `str` | Unique identifier (UUID) |
| `name` | `str` | Human-readable account name |
| `balance` | `float` | Available cash balance |
| `holdings` | `dict[str, int]` | Symbol → quantity owned |
| `transactions` | `list[Transaction]` | Ordered list of all transactions |
| `initial_deposit` | `float` | Total amount ever deposited (used for P&L calculation) |
| `total_deposited` | `float` | Cumulative sum of all deposits |
| `total_withdrawn` | `float` | Cumulative sum of all withdrawals |
| `created_at` | `datetime` | Account creation timestamp |

Method signatures:

```
def to_dict() -> dict:
    """Serialize account summary to a dictionary."""

@staticmethod
def from_dict(data: dict) -> Account:
    """Deserialize a dictionary back to an Account."""
```

---

### 2.3. `SharePriceProvider` Class

Provides share prices. Includes a default test implementation.

```
class SharePriceProvider:
    """Interface/base for share price lookup."""

    def get_share_price(self, symbol: str) -> float:
        """Return the current price for the given symbol. Raises ValueError if symbol unknown."""
```

```
class TestSharePriceProvider(SharePriceProvider):
    """Test implementation returning fixed prices for AAPL, TSLA, GOOGL."""

    FIXED_PRICES: dict[str, float]  # {"AAPL": 150.0, "TSLA": 250.0, "GOOGL": 2800.0}

    def __init__(self, prices: Optional[dict[str, float]] = None):
        """Initialize with optional custom price mapping."""

    def get_share_price(self, symbol: str) -> float:
        """Return the fixed price. Raises ValueError if symbol not in mapping."""
```

---

### 2.4. `AccountManager` Class

The core business logic class. Manages all accounts and operations.

```
class AccountManager:
    """Manages multiple trading accounts and all portfolio operations."""

    def __init__(self, price_provider: Optional[SharePriceProvider] = None):
        """
        Initialize the manager.
        If no price_provider is given, defaults to TestSharePriceProvider().
        """

    # ── Account CRUD ─────────────────────────────────────────────

    def create_account(self, name: str, initial_deposit: float) -> Account:
        """
        Create a new account with the given name and initial deposit.
        initial_deposit must be >= 0.
        Returns the newly created Account.
        Records the initial deposit as a DEPOSIT transaction.
        """

    def get_account(self, account_id: str) -> Account:
        """Return the Account with the given ID. Raises KeyError if not found."""

    def list_accounts(self) -> list[Account]:
        """Return all accounts."""

    def delete_account(self, account_id: str) -> None:
        """Delete the account with the given ID. Raises KeyError if not found."""

    # ── Cash Operations ──────────────────────────────────────────

    def deposit(self, account_id: str, amount: float) -> Transaction:
        """
        Deposit the given amount into the specified account.
        amount must be > 0.
        Updates balance and total_deposited.
        Returns the DEPOSIT Transaction.
        """

    def withdraw(self, account_id: str, amount: float) -> Transaction:
        """
        Withdraw the given amount from the specified account.
        amount must be > 0.
        Raises ValueError if withdrawal would result in negative balance.
        Updates balance and total_withdrawn.
        Returns the WITHDRAW Transaction.
        """

    # ── Trading Operations ───────────────────────────────────────

    def buy_shares(self, account_id: str, symbol: str, quantity: int) -> Transaction:
        """
        Buy the given quantity of shares for the specified symbol.
        quantity must be > 0.
        Uses SharePriceProvider to get current price.
        Raises ValueError if the total cost exceeds available balance.
        Updates balance (deducts cost) and holdings.
        Returns the BUY Transaction.
        """

    def sell_shares(self, account_id: str, symbol: str, quantity: int) -> Transaction:
        """
        Sell the given quantity of shares for the specified symbol.
        quantity must be > 0.
        Uses SharePriceProvider to get current price.
        Raises ValueError if the account does not hold enough shares.
        Updates balance (adds proceeds) and holdings.
        Returns the SELL Transaction.
        """

    # ── Reporting ────────────────────────────────────────────────

    def get_holdings(self, account_id: str) -> dict[str, int]:
        """
        Return a dict of symbol → quantity for the account.
        Only includes symbols with quantity > 0.
        """

    def get_portfolio_value(self, account_id: str) -> float:
        """
        Calculate total portfolio value.
        = cash balance + sum(quantity * current_price) for each holding.
        Uses SharePriceProvider for current prices.
        """

    def get_profit_loss(self, account_id: str) -> float:
        """
        Calculate profit/loss relative to net deposits.
        = (portfolio_value + total_withdrawn) - total_deposited.
        """

    def get_transactions(self, account_id: str) -> list[Transaction]:
        """Return the full list of transactions for the account, in chronological order."""

    def get_transactions_filtered(
        self,
        account_id: str,
        transaction_type: Optional[TransactionType] = None,
        symbol: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
    ) -> list[Transaction]:
        """Return filtered transactions for the account."""

    def get_account_summary(self, account_id: str) -> dict:
        """
        Return a summary dict with keys:
        - account_id, name, balance
        - holdings (dict)
        - portfolio_value
        - profit_loss
        - total_deposited, total_withdrawn
        - transaction_count
        """

    def get_all_account_summaries(self) -> list[dict]:
        """Return summary dicts for all accounts."""

    # ── Internal Helpers ─────────────────────────────────────────

    def _validate_balance_for_withdrawal(self, account: Account, amount: float) -> None:
        """Raises ValueError if withdrawal amount exceeds balance."""

    def _validate_balance_for_purchase(self, account: Account, total_cost: float) -> None:
        """Raises ValueError if purchase cost exceeds balance."""

    def _validate_holdings_for_sale(self, account: Account, symbol: str, quantity: int) -> None:
        """Raises ValueError if account holds fewer shares than quantity."""
```

---

### 2.5. Module-Level Convenience Functions

For cases where a singleton manager is sufficient:

```
# Module-level singleton instance

_default_manager: Optional[AccountManager] = None

def get_default_manager() -> AccountManager:
    """Return (or create) the module-level singleton AccountManager."""

def reset_manager() -> None:
    """Reset the singleton to a fresh AccountManager."""
```

---

## 3. Frontend Module (`app.py`)

Built with Gradio. The UI follows a two-tier tab structure.

### 3.1. UI Layout Architecture

```
┌──────────────────────────────────────────────────────────┐
│  [Profile ▾]  [Create New Account]                        │  ← Upper Tab Row (always visible)
├──────────────────────────────────────────────────────────┤
│  [Deposit] [Withdraw] [Buy Shares] [Sell Shares]         │  ← Lower Tab Row
│  [Holdings] [Profit/Loss] [Transactions]                  │     (visible only when account selected)
├──────────────────────────────────────────────────────────┤
│                                                          │
│  Active Tab Content Area                                 │  ← Scrollable content
│  (data displayed here, scrollable if overflows)          │
│                                                          │
└──────────────────────────────────────────────────────────┘
```

### 3.2. UI States

#### State A: No accounts exist
- Upper tabs: `[Profile (empty state)] [Create New Account]`
- Lower tabs: **hidden**
- Profile tab shows: "No accounts yet. Create one using the 'Create New Account' tab."

#### State B: Accounts exist, none selected
- Upper tabs: `[Profile (dropdown)] [Create New Account]`
- Lower tabs: **hidden**
- Profile tab shows account selection dropdown and a "Select Account" button.

#### State C: Account selected
- Upper tabs: `[Profile (showing selected)] [Create New Account]`
- Lower tabs: `[Deposit] [Withdraw] [Buy Shares] [Sell Shares] [Holdings] [Profit/Loss] [Transactions]`
- Data is specific to the selected account.

### 3.3. Gradio Application Class

```
class TradingSimulationApp:
    """Gradio application for the trading simulation account management system."""

    def __init__(self):
        """Initialize the AccountManager and build the Gradio Blocks UI."""

    def build(self) -> gr.Blocks:
        """Construct and return the Gradio Blocks interface."""

    def launch(self, **kwargs):
        """Launch the Gradio app."""
```

### 3.4. UI Building Method Signatures

```
def _build_upper_tabs(self) -> tuple[gr.Tab, gr.Tab]:
    """
    Build the upper tab row: Profile tab and Create New Account tab.
    Returns references to both tab objects.
    """

def _build_lower_tabs(self) -> dict[str, gr.Tab]:
    """
    Build the lower tab row with Deposit, Withdraw, Buy Shares, Sell Shares,
    Holdings, Profit/Loss, and Transactions tabs.
    Returns a dict mapping tab name to tab object.
    """

def _build_profile_tab(self) -> None:
    """
    Build content for the Profile tab:
    - Account selection dropdown (populated from AccountManager)
    - Display current account summary (balance, holdings count, P&L)
    - "Select Account" button
    """

def _build_create_account_tab(self) -> None:
    """
    Build content for the Create New Account tab:
    - Account name input
    - Initial deposit input
    - "Create Account" button
    - Feedback/success message area
    """

def _build_deposit_tab(self) -> None:
    """
    Build content for the Deposit tab:
    - Amount input
    - "Deposit" button
    - Updated balance display
    - Feedback area
    """

def _build_withdraw_tab(self) -> None:
    """
    Build content for the Withdraw tab:
    - Amount input
    - "Withdraw" button
    - Updated balance display
    - Error/feedback area (for insufficient funds)
    """

def _build_buy_shares_tab(self) -> None:
    """
    Build content for the Buy Shares tab:
    - Symbol dropdown (AAPL, TSLA, GOOGL)
    - Quantity input
    - Display current price (fetched from backend)
    - Display estimated total cost
    - "Buy" button
    - Error/feedback area (for insufficient funds)
    """

def _build_sell_shares_tab(self) -> None:
    """
    Build content for the Sell Shares tab:
    - Symbol dropdown (AAPL, TSLA, GOOGL)
    - Quantity input
    - Display current price
    - Display current holdings for selected symbol
    - "Sell" button
    - Error/feedback area (for insufficient holdings)
    """

def _build_holdings_tab(self) -> None:
    """
    Build content for the Holdings tab:
    - Table/grid showing symbol, quantity, current price, current value
    - Total portfolio value display
    - Scrollable if many holdings
    """

def _build_profit_loss_tab(self) -> None:
    """
    Build content for the Profit/Loss tab:
    - Total deposited display
    - Total withdrawn display
    - Current portfolio value display
    - Net profit/loss display (with color: green positive, red negative)
    """

def _build_transactions_tab(self) -> None:
    """
    Build content for the Transactions tab:
    - Scrollable table of all transactions
    - Columns: Timestamp, Type, Symbol, Quantity, Price, Amount
    - Optional filter controls (by type, symbol)
    """
```

### 3.5. Event Handler Method Signatures

```
def _on_create_account(self, name: str, initial_deposit: float) -> tuple:
    """
    Handle account creation.
    Returns updated UI state: account dropdown, success message, visibility flags.
    """

def _on_select_account(self, account_id: str) -> tuple:
    """
    Handle account selection from dropdown.
    Returns: updated summary data, make lower tabs visible, clear previous data.
    """

def _on_deposit(self, account_id: str, amount: float) -> tuple:
    """
    Handle deposit. Returns updated balance and feedback message.
    """

def _on_withdraw(self, account_id: str, amount: float) -> tuple:
    """
    Handle withdrawal. Returns updated balance, success/error message.
    """

def _on_buy_shares(self, account_id: str, symbol: str, quantity: int) -> tuple:
    """
    Handle share purchase. Returns updated balance, holdings, success/error.
    """

def _on_sell_shares(self, account_id: str, symbol: str, quantity: int) -> tuple:
    """
    Handle share sale. Returns updated balance, holdings, success/error.
    """

def _on_refresh_holdings(self, account_id: str) -> tuple:
    """
    Refresh holdings display. Returns holdings data for the table.
    """

def _on_refresh_profit_loss(self, account_id: str) -> tuple:
    """
    Refresh P&L display.
    """

def _on_refresh_transactions(self, account_id: str) -> tuple:
    """
    Refresh transactions table.
    """

def _on_get_current_price(self, symbol: str) -> float:
    """
    Return the current price for the given symbol (for display in Buy/Sell tabs).
    """

def _clear_all_data(self) -> tuple:
    """
    Clear all displayed data when switching accounts.
    Returns default/empty values for all UI components.
    """
```

### 3.6. Gradio State Management

```
# Gradio State variables maintained in the Blocks:

selected_account_id: gr.State  # str or None
account_manager: gr.State       # AccountManager instance
```

### 3.7. Styling & Theming

- Use `gr.themes.Soft()` or `gr.themes.Base()` with dark mode enabled.
- Apply custom CSS for:
  - Responsive layout (flex-based, max-width containers)
  - Modern color palette (dark backgrounds, accent colors for actions)
  - Proper font sizing and spacing
  - Scrollable content areas with `overflow-y: auto` and max-height constraints
  - Icons via emoji or Unicode characters in labels
  - Color-coded P&L: green (`#4CAF50`) for positive, red (`#F44336`) for negative

---

## 4. Test Module (`test_portfolio_manager.py`)

Uses `pytest`. Tests the backend `AccountManager` class in isolation.

### 4.1. Test Fixtures

```
@pytest.fixture
def price_provider() -> TestSharePriceProvider:
    """Return a fresh TestSharePriceProvider with default prices."""

@pytest.fixture
def manager(price_provider: TestSharePriceProvider) -> AccountManager:
    """Return a fresh AccountManager with the test price provider."""

@pytest.fixture
def account(manager: AccountManager) -> Account:
    """Create and return a default account with $10,000 initial deposit."""
```

### 4.2. Test Classes & Methods

#### `TestAccountCreation`

```
class TestAccountCreation:
    """Tests for account creation functionality."""

    def test_create_account_succeeds(self, manager: AccountManager):
        """Creating an account with valid name and deposit returns an Account."""

    def test_create_account_records_deposit_transaction(self, manager: AccountManager):
        """The initial deposit is recorded as a DEPOSIT transaction."""

    def test_create_account_zero_deposit(self, manager: AccountManager):
        """Creating an account with 0 initial deposit is allowed."""

    def test_create_account_negative_deposit_raises(self, manager: AccountManager):
        """Creating an account with negative deposit raises ValueError."""

    def test_create_account_empty_name_raises(self, manager: AccountManager):
        """Empty account name raises ValueError."""

    def test_list_accounts(self, manager: AccountManager):
        """list_accounts returns all created accounts."""

    def test_get_account_by_id(self, manager: AccountManager):
        """get_account returns the correct account."""

    def test_get_account_invalid_id_raises(self, manager: AccountManager):
        """get_account with invalid ID raises KeyError."""

    def test_delete_account(self, manager: AccountManager):
        """delete_account removes the account."""

    def test_delete_account_invalid_id_raises(self, manager: AccountManager):
        """delete_account with invalid ID raises KeyError."""
```

#### `TestDeposit`

```
class TestDeposit:
    """Tests for deposit functionality."""

    def test_deposit_increases_balance(self, manager: AccountManager, account: Account):
        """Depositing funds increases the account balance."""

    def test_deposit_records_transaction(self, manager: AccountManager, account: Account):
        """Deposit creates a DEPOSIT transaction with correct amount."""

    def test_deposit_zero_amount_raises(self, manager: AccountManager, account: Account):
        """Depositing 0 raises ValueError."""

    def test_deposit_negative_amount_raises(self, manager: AccountManager, account: Account):
        """Depositing negative amount raises ValueError."""
```

#### `TestWithdrawal`

```
class TestWithdrawal:
    """Tests for withdrawal functionality."""

    def test_withdraw_decreases_balance(self, manager: AccountManager, account: Account):
        """Withdrawing funds decreases the balance."""

    def test_withdraw_records_transaction(self, manager: AccountManager, account: Account):
        """Withdrawal creates a WITHDRAW transaction."""

    def test_withdraw_insufficient_funds_raises(self, manager: AccountManager, account: Account):
        """Withdrawing more than balance raises ValueError."""

    def test_withdraw_exact_balance_succeeds(self, manager: AccountManager, account: Account):
        """Withdrawing exactly the balance amount succeeds."""

    def test_withdraw_zero_amount_raises(self, manager: AccountManager, account: Account):
        """Withdrawing 0 raises ValueError."""

    def test_withdraw_negative_amount_raises(self, manager: AccountManager, account: Account):
        """Withdrawing negative amount raises ValueError."""
```

#### `TestBuyShares`

```
class TestBuyShares:
    """Tests for buying shares."""

    def test_buy_shares_deducts_balance(self, manager: AccountManager, account: Account):
        """Buying shares deducts (quantity * price) from balance."""

    def test_buy_shares_increases_holdings(self, manager: AccountManager, account: Account):
        """Buying shares adds to holdings for the symbol."""

    def test_buy_shares_records_transaction(self, manager: AccountManager, account: Account):
        """Buy creates a BUY transaction with symbol, quantity, and price."""

    def test_buy_multiple_lots_accumulates(self, manager: AccountManager, account: Account):
        """Buying the same symbol multiple times accumulates quantity."""

    def test_buy_zero_quantity_raises(self, manager: AccountManager, account: Account):
        """Buying 0 shares raises ValueError."""

    def test_buy_negative_quantity_raises(self, manager: AccountManager, account: Account):
        """Buying negative shares raises ValueError."""

    def test_buy_insufficient_funds_raises(self, manager: AccountManager, account: Account):
        """Buying shares that cost more than balance raises ValueError."""

    def test_buy_unknown_symbol_raises(self, manager: AccountManager, account: Account):
        """Buying an unknown symbol raises ValueError from price provider."""

    def test_buy_spends_exact_balance_succeeds(self, manager: AccountManager, account: Account):
        """Buying shares that cost exactly the balance succeeds."""
```

#### `TestSellShares`

```
class TestSellShares:
    """Tests for selling shares."""

    def test_sell_shares_increases_balance(self, manager: AccountManager, account: Account):
        """Selling shares adds proceeds to balance."""

    def test_sell_shares_decreases_holdings(self, manager: AccountManager, account: Account):
        """Selling shares reduces holdings for the symbol."""

    def test_sell_shares_records_transaction(self, manager: AccountManager, account: Account):
        """Sell creates a SELL transaction."""

    def test_sell_partial_holdings(self, manager: AccountManager, account: Account):
        """Selling fewer shares than held leaves remaining holdings."""

    def test_sell_all_holdings_removes_symbol(self, manager: AccountManager, account: Account):
        """Selling all shares removes the symbol from holdings."""

    def test_sell_zero_quantity_raises(self, manager: AccountManager, account: Account):
        """Selling 0 shares raises ValueError."""

    def test_sell_negative_quantity_raises(self, manager: AccountManager, account: Account):
        """Selling negative shares raises ValueError."""

    def test_sell_more_than_held_raises(self, manager: AccountManager, account: Account):
        """Selling more shares than held raises ValueError."""

    def test_sell_unheld_symbol_raises(self, manager: AccountManager, account: Account):
        """Selling a symbol with zero holdings raises ValueError."""

    def test_sell_unknown_symbol_raises(self, manager: AccountManager, account: Account):
        """Selling an unknown symbol raises ValueError from price provider."""
```

#### `TestPortfolioValue`

```
class TestPortfolioValue:
    """Tests for portfolio valuation."""

    def test_portfolio_value_cash_only(self, manager: AccountManager, account: Account):
        """Portfolio value with no holdings equals balance."""

    def test_portfolio_value_includes_holdings(self, manager: AccountManager, account: Account):
        """Portfolio value = balance + market value of holdings."""

    def test_portfolio_value_zero_balance_and_holdings(self, manager: AccountManager):
        """Portfolio value of a new account with 0 deposit is 0."""

    def test_portfolio_value_after_buy_and_price_change(self, manager: AccountManager, account: Account):
        """Portfolio value reflects current market prices, not purchase prices."""
```

#### `TestProfitLoss`

```
class TestProfitLoss:
    """Tests for profit/loss calculation."""

    def test_profit_loss_zero_with_no_activity(self, manager: AccountManager, account: Account):
        """P&L is 0 when no trading activity and no withdrawals."""

    def test_profit_loss_positive_after_gain(self, manager: AccountManager, account: Account):
        """P&L is positive when portfolio value exceeds net deposits."""

    def test_profit_loss_negative_after_loss(self, manager: AccountManager, account: Account):
        """P&L is negative when portfolio value is below net deposits."""

    def test_profit_loss_accounts_for_withdrawals(self, manager: AccountManager, account: Account):
        """P&L formula: (portfolio_value + total_withdrawn) - total_deposited."""
```

#### `TestHoldings`

```
class TestHoldings:
    """Tests for holdings reporting."""

    def test_get_holdings_empty_initially(self, manager: AccountManager, account: Account):
        """New account has empty holdings."""

    def test_get_holdings_returns_only_nonzero(self, manager: AccountManager, account: Account):
        """Holdings dict excludes symbols with quantity 0."""

    def test_get_holdings_multiple_symbols(self, manager: AccountManager, account: Account):
        """Holdings correctly tracks multiple symbols."""
```

#### `TestTransactions`

```
class TestTransactions:
    """Tests for transaction listing."""

    def test_get_transactions_chronological(self, manager: AccountManager, account: Account):
        """Transactions are returned in chronological order."""

    def test_get_transactions_filtered_by_type(self, manager: AccountManager, account: Account):
        """Filtering by TransactionType returns only matching transactions."""

    def test_get_transactions_filtered_by_symbol(self, manager: AccountManager, account: Account):
        """Filtering by symbol returns only transactions for that symbol."""

    def test_get_transactions_filtered_by_time_range(self, manager: AccountManager, account: Account):
        """Filtering by time range returns transactions within that window."""
```

#### `TestSharePriceProvider`

```
class TestSharePriceProvider:
    """Tests for the test price provider."""

    def test_returns_fixed_price_for_aapl(self):
        """get_share_price('AAPL') returns 150.0."""

    def test_returns_fixed_price_for_tsla(self):
        """get_share_price('TSLA') returns 250.0."""

    def test_returns_fixed_price_for_googl(self):
        """get_share_price('GOOGL') returns 2800.0."""

    def test_unknown_symbol_raises(self):
        """get_share_price('UNKNOWN') raises ValueError."""

    def test_custom_prices(self):
        """Custom price mapping overrides defaults."""
```

---

## 5. File Structure

```
sandbox/
├── pyproject.toml          # uv project config with gradio dependency
├── portfolio_manager.py    # Backend: AccountManager, Account, Transaction, SharePriceProvider
├── app.py                  # Frontend: Gradio TradingSimulationApp
└── test_portfolio_manager.py  # Tests: pytest unit tests for backend
```

---

## 6. Data Flow Summary

```
┌──────────┐    Gradio Events     ┌──────────┐    Method Calls     ┌────────────────────┐
│  app.py  │ ◄──────────────────► │  app.py  │ ◄─────────────────► │ portfolio_manager  │
│  (UI)    │    (callbacks)       │ (State)  │                    │   .py (Logic)      │
└──────────┘                      └──────────┘                    └────────────────────┘
                                                                          │
                                                                          │ get_share_price()
                                                                          ▼
                                                                  ┌────────────────────┐
                                                                  │ SharePriceProvider │
                                                                  └────────────────────┘
```

- All state lives in the `AccountManager` instance (held in `gr.State`).
- UI callbacks call manager methods, receive results, and update UI components.
- Data is never persisted to disk — all in memory for the session.
- Switching accounts triggers `_clear_all_data()` then populates with the new account's data.

---

## 7. Validation Rules Summary

| Operation | Rule | Error |
|---|---|---|
| `create_account` | `initial_deposit >= 0`, `name` non-empty | `ValueError` |
| `deposit` | `amount > 0` | `ValueError` |
| `withdraw` | `amount > 0` AND `amount <= balance` | `ValueError` |
| `buy_shares` | `quantity > 0` AND `quantity * price <= balance` AND symbol valid | `ValueError` |
| `sell_shares` | `quantity > 0` AND `quantity <= holdings[symbol]` AND symbol valid | `ValueError` |

---

## 8. Key Design Decisions

1. **In-memory storage**: No database; all state in `AccountManager`. Sufficient for a simulation platform and simplifies testing.

2. **Singleton pattern optional**: The `AccountManager` can be used as a singleton via `get_default_manager()` for simple apps, or instantiated directly for isolation in tests.

3. **Fixed test prices**: `TestSharePriceProvider` returns static prices. This makes tests deterministic and the simulation predictable. A real implementation would implement `SharePriceProvider` with an API call.

4. **P&L formula**: `(portfolio_value + total_withdrawn) - total_deposited`. This treats deposits as cost basis and withdrawals as realized returns, giving a true economic P&L.

5. **Transaction immutability**: Transactions, once created, are appended and never modified — providing a complete audit trail.

6. **Gradio `gr.State`**: Used to hold the `AccountManager` instance and the currently selected `account_id` across UI interactions without needing a database.

7. **All files in one directory**: As specified, no subdirectories. The `uv` project keeps dependencies in `pyproject.toml`.