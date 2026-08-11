# Trading Simulation Account Management System — Engineering Design

## 1. Purpose

Build a simple account management system for a trading simulation platform.

The system must allow users to:

- Create an account.
- Deposit funds.
- Withdraw funds.
- Buy shares.
- Sell shares.
- View current holdings.
- View holdings at a point in time.
- View portfolio value.
- View profit/loss at a point in time.
- List transactions over time.

The system must prevent:

- Withdrawals that would make the cash balance negative.
- Buying shares the user cannot afford.
- Selling shares the user does not own.

The backend has access to:

```python
get_share_price(symbol)
```

This function returns the current share price for supported symbols.

Supported test symbols:

| Symbol | Fixed Test Price |
|---|---:|
| `AAPL` | `150.00` |
| `TSLA` | `250.00` |
| `GOOGL` | `2800.00` |

---

## 2. Project Structure

All files must be placed in the same sandbox directory.

No package directories are required.

```text
models.py
exceptions.py
price_service.py
repository.py
account_service.py
formatters.py
app.py
test_price_service.py
test_account_service.py
test_point_in_time.py
test_transactions.py
test_frontend_handlers.py
```

---

## 3. Team Responsibilities

## 3.1 `backend_engineer`

Responsible for:

- Backend Python domain model.
- Account creation.
- Deposits and withdrawals.
- Buy and sell operations.
- Transaction recording.
- Holdings calculation.
- Portfolio valuation.
- Profit/loss calculation.
- Point-in-time reporting.
- Backend validation and exceptions.
- In-memory persistence.

Primary files:

```text
models.py
exceptions.py
price_service.py
repository.py
account_service.py
```

---

## 3.2 `frontend_engineer`

Responsible for:

- Gradio frontend.
- Calling backend service methods.
- Displaying accounts, holdings, valuation, P&L, and transactions.
- Handling user input.
- Displaying user-friendly success/error messages.

Primary files:

```text
app.py
formatters.py
```

---

## 3.3 `test_engineer`

Responsible for:

- Unit tests for backend modules.
- Unit tests for frontend handler functions.
- Validation tests.
- Point-in-time tests.
- Transaction history tests.

Primary files:

```text
test_price_service.py
test_account_service.py
test_point_in_time.py
test_transactions.py
test_frontend_handlers.py
```

Tests should run with:

```text
uv run python -m unittest discover -s . -p "test_*.py"
```

---

# 4. Domain Rules

## 4.1 Account

An account represents one user’s trading simulation account.

An account has:

- Unique account ID.
- Owner name.
- Creation timestamp.
- Initial deposit amount.
- Monotonically increasing transaction sequence.
- Transaction list.

The current cash balance and holdings should be calculated from transactions.

---

## 4.2 Transactions

Every account-changing action should create a transaction.

Transaction types:

```text
DEPOSIT
WITHDRAWAL
BUY
SELL
```

Each transaction records:

- Transaction ID.
- Account ID.
- Sequence number.
- Transaction type.
- Timestamp.
- Cash delta.
- Symbol, if applicable.
- Quantity, if applicable.
- Execution price, if applicable.
- Optional notes.

Transactions should be append-only.

Failed operations must not create transactions.

---

## 4.3 Cash Balance

Cash balance is derived from transaction history.

```text
cash balance =
  total deposits
- total withdrawals
- total buy costs
+ total sell proceeds
```

A user cannot withdraw if the resulting cash balance would be negative.

A user cannot buy shares if the buy cost exceeds available cash.

---

## 4.4 Holdings

Holdings are derived from buy and sell transactions.

For each symbol:

```text
holding quantity =
  total quantity bought
- total quantity sold
```

A user cannot sell more shares than currently held.

Symbols with zero quantity should be omitted from holdings reports.

---

## 4.5 Portfolio Value

Portfolio value is:

```text
portfolio value =
  current cash balance
+ market value of current holdings
```

Where:

```text
market value of symbol =
  quantity held * current share price
```

---

## 4.6 Profit/Loss

Profit/loss should be calculated against net external contributions.

```text
net external contributions =
  total deposits
- total withdrawals
```

```text
profit/loss =
  portfolio value
- net external contributions
```

This prevents withdrawals from incorrectly appearing as trading losses.

Example:

```text
Initial deposit: 1000
Withdrawal: 200
Cash balance: 800
Holdings value: 0
Portfolio value: 800
Net external contributions: 800
Profit/loss: 0
```

---

## 4.7 Point-in-Time Reporting

Point-in-time reports should include transactions where:

```text
transaction.timestamp <= as_of
```

If `as_of` is `None`, all transactions are included.

The system only has current prices from `get_share_price(symbol)`.

Therefore:

- Point-in-time holdings should be historically accurate.
- Point-in-time cash should be historically accurate.
- Point-in-time transaction lists should be historically accurate.
- Point-in-time valuation should use current prices because no historical price API exists.

The valuation API should still accept `as_of` so historical pricing can be added later.

---

## 4.8 Numeric Rules

Use Python `Decimal` internally for:

- Cash amounts.
- Share prices.
- Quantities.
- Portfolio values.
- Profit/loss.

Validation rules:

- Deposit amount must be greater than zero.
- Withdrawal amount must be greater than zero.
- Initial deposit must be greater than or equal to zero.
- Buy quantity must be greater than zero.
- Sell quantity must be greater than zero.
- Share price must be greater than zero.
- Fractional share quantities are allowed.

No commissions, fees, taxes, or spreads are applied.

---

# 5. `exceptions.py`

Defines backend domain exceptions.

## Classes

```python
class TradingAppError(Exception)
```

Base exception for all expected application errors.

```python
class ValidationError(TradingAppError)
```

Raised when user input is invalid.

```python
class AccountNotFoundError(TradingAppError)
```

Raised when an account ID does not exist.

```python
class InsufficientFundsError(TradingAppError)
```

Raised when a withdrawal or buy would exceed available cash.

```python
class InsufficientHoldingsError(TradingAppError)
```

Raised when a sell quantity exceeds available holdings.

```python
class UnknownSymbolError(TradingAppError)
```

Raised when a requested share symbol is unsupported.

```python
class PriceLookupError(TradingAppError)
```

Raised when a price cannot be retrieved.

---

# 6. `models.py`

Contains dataclasses and transaction type constants.

## 6.1 Transaction Type Constants

```python
TRANSACTION_TYPE_DEPOSIT: str
TRANSACTION_TYPE_WITHDRAWAL: str
TRANSACTION_TYPE_BUY: str
TRANSACTION_TYPE_SELL: str
```

Allowed values:

```text
DEPOSIT
WITHDRAWAL
BUY
SELL
```

---

## 6.2 `Transaction`

Represents one immutable financial event.

```python
@dataclass(frozen=True)
class Transaction:
    transaction_id: str
    account_id: str
    sequence: int
    transaction_type: str
    timestamp: datetime
    cash_delta: Decimal
    symbol: str | None
    quantity: Decimal | None
    execution_price: Decimal | None
    notes: str | None
```

Field rules:

| Field | Rule |
|---|---|
| `transaction_id` | Globally unique string |
| `account_id` | Parent account ID |
| `sequence` | Monotonic per account |
| `transaction_type` | One of `DEPOSIT`, `WITHDRAWAL`, `BUY`, `SELL` |
| `timestamp` | Timezone-aware UTC datetime |
| `cash_delta` | Signed cash movement |
| `symbol` | Required for buy/sell, otherwise `None` |
| `quantity` | Required for buy/sell, otherwise `None` |
| `execution_price` | Required for buy/sell, otherwise `None` |
| `notes` | Optional text |

---

## 6.3 `Account`

Represents a user account.

```python
@dataclass
class Account:
    account_id: str
    owner_name: str
    created_at: datetime
    initial_deposit: Decimal
    next_sequence: int
    transactions: list[Transaction]
```

Rules:

- `next_sequence` starts at `1`.
- Each new transaction receives the current `next_sequence`.
- After creating a transaction, `next_sequence` increments by `1`.

---

## 6.4 `Holding`

Represents a calculated holding.

```python
@dataclass(frozen=True)
class Holding:
    symbol: str
    quantity: Decimal
```

---

## 6.5 `PositionValuation`

Represents valuation for one holding.

```python
@dataclass(frozen=True)
class PositionValuation:
    symbol: str
    quantity: Decimal
    price: Decimal
    market_value: Decimal
```

---

## 6.6 `PortfolioValuation`

Represents a full portfolio valuation.

```python
@dataclass(frozen=True)
class PortfolioValuation:
    account_id: str
    as_of: datetime | None
    cash_balance: Decimal
    positions: list[PositionValuation]
    securities_value: Decimal
    total_value: Decimal
    net_external_contributions: Decimal
    profit_loss: Decimal
```

---

# 7. `price_service.py`

Provides share price access.

## 7.1 Required Function

```python
def get_share_price(symbol: str) -> float
```

Rules:

- Accepts stock symbol.
- Supports `AAPL`, `TSLA`, and `GOOGL`.
- Returns fixed test prices.
- Should raise or allow wrapping into `UnknownSymbolError` for unsupported symbols.

Expected fixed prices:

```text
AAPL: 150.00
TSLA: 250.00
GOOGL: 2800.00
```

---

## 7.2 `PriceService`

Wrapper around `get_share_price`.

```python
class PriceService:
    def get_price(
        self,
        symbol: str,
        as_of: datetime | None = None,
    ) -> Decimal
```

Rules:

- Normalize symbol to uppercase.
- Call `get_share_price(symbol)`.
- Convert returned price to `Decimal`.
- Ignore `as_of` in current implementation.
- Raise `UnknownSymbolError` for unsupported symbols.
- Raise `PriceLookupError` for unexpected lookup failures.

---

# 8. `repository.py`

Provides in-memory account storage.

## 8.1 `InMemoryAccountRepository`

```python
class InMemoryAccountRepository:
    def __init__(self) -> None

    def add_account(
        self,
        account: Account,
    ) -> None

    def get_account(
        self,
        account_id: str,
    ) -> Account

    def save_account(
        self,
        account: Account,
    ) -> None

    def list_accounts(
        self,
    ) -> list[Account]

    def account_exists(
        self,
        account_id: str,
    ) -> bool
```

Rules:

- `get_account` raises `AccountNotFoundError` if missing.
- `save_account` raises `AccountNotFoundError` if missing.
- Storage is process-local and resets when the app restarts.
- No database is required.

---

# 9. `account_service.py`

Main backend business logic.

## 9.1 `AccountService`

```python
class AccountService:
    def __init__(
        self,
        repository: InMemoryAccountRepository,
        price_service: PriceService,
    ) -> None
```

The service should own a lock to protect mutating operations because the Gradio app may receive concurrent events.

---

## 9.2 Account Methods

```python
def create_account(
    self,
    owner_name: str,
    initial_deposit: Decimal,
    timestamp: datetime | None = None,
) -> Account
```

Rules:

- Owner name is required.
- Initial deposit must be greater than or equal to zero.
- Creates account.
- If initial deposit is greater than zero, creates an initial `DEPOSIT` transaction.
- Returns created account.

---

```python
def get_account(
    self,
    account_id: str,
) -> Account
```

Rules:

- Returns account.
- Raises `AccountNotFoundError` if not found.

---

```python
def list_accounts(
    self,
) -> list[Account]
```

Rules:

- Returns all accounts.

---

## 9.3 Cash Operation Methods

```python
def deposit(
    self,
    account_id: str,
    amount: Decimal,
    timestamp: datetime | None = None,
    notes: str | None = None,
) -> Transaction
```

Rules:

- Account must exist.
- Amount must be greater than zero.
- Creates a `DEPOSIT` transaction.
- Cash delta is positive.

---

```python
def withdraw(
    self,
    account_id: str,
    amount: Decimal,
    timestamp: datetime | None = None,
    notes: str | None = None,
) -> Transaction
```

Rules:

- Account must exist.
- Amount must be greater than zero.
- Current cash balance must be greater than or equal to withdrawal amount.
- Creates a `WITHDRAWAL` transaction.
- Cash delta is negative.
- If validation fails, no transaction is created.

---

## 9.4 Trading Methods

```python
def buy_shares(
    self,
    account_id: str,
    symbol: str,
    quantity: Decimal,
    timestamp: datetime | None = None,
    notes: str | None = None,
) -> Transaction
```

Rules:

- Account must exist.
- Symbol is required.
- Symbol is normalized to uppercase.
- Quantity must be greater than zero.
- Current price is retrieved from `PriceService`.
- Buy cost is `quantity * execution_price`.
- Current cash balance must be greater than or equal to buy cost.
- Creates a `BUY` transaction.
- Cash delta is negative.
- Execution price is stored on transaction.
- If validation fails, no transaction is created.

---

```python
def sell_shares(
    self,
    account_id: str,
    symbol: str,
    quantity: Decimal,
    timestamp: datetime | None = None,
    notes: str | None = None,
) -> Transaction
```

Rules:

- Account must exist.
- Symbol is required.
- Symbol is normalized to uppercase.
- Quantity must be greater than zero.
- Current holdings for symbol must be greater than or equal to sell quantity.
- Current price is retrieved from `PriceService`.
- Sell proceeds are `quantity * execution_price`.
- Creates a `SELL` transaction.
- Cash delta is positive.
- Execution price is stored on transaction.
- If validation fails, no transaction is created.

---

## 9.5 Reporting Methods

```python
def get_cash_balance(
    self,
    account_id: str,
    as_of: datetime | None = None,
) -> Decimal
```

Returns cash balance as of a timestamp.

---

```python
def get_holdings(
    self,
    account_id: str,
    as_of: datetime | None = None,
) -> list[Holding]
```

Returns holdings as of a timestamp.

---

```python
def get_portfolio_valuation(
    self,
    account_id: str,
    as_of: datetime | None = None,
) -> PortfolioValuation
```

Returns full portfolio valuation as of a timestamp.

The transaction state is calculated as of `as_of`.

Prices are current prices from `PriceService`.

---

```python
def get_profit_loss(
    self,
    account_id: str,
    as_of: datetime | None = None,
) -> Decimal
```

Returns profit/loss as of a timestamp.

---

```python
def get_net_external_contributions(
    self,
    account_id: str,
    as_of: datetime | None = None,
) -> Decimal
```

Returns:

```text
deposits as of timestamp - withdrawals as of timestamp
```

---

```python
def list_transactions(
    self,
    account_id: str,
    start_time: datetime | None = None,
    end_time: datetime | None = None,
) -> list[Transaction]
```

Rules:

- Returns account transactions sorted by sequence.
- If `start_time` is provided, include transactions where `timestamp >= start_time`.
- If `end_time` is provided, include transactions where `timestamp <= end_time`.

---

## 9.6 Internal Helper Methods

```python
def _create_transaction(
    self,
    account: Account,
    transaction_type: str,
    timestamp: datetime,
    cash_delta: Decimal,
    symbol: str | None,
    quantity: Decimal | None,
    execution_price: Decimal | None,
    notes: str | None,
) -> Transaction
```

---

```python
def _get_effective_timestamp(
    self,
    timestamp: datetime | None,
) -> datetime
```

Rules:

- If timestamp is provided, use it.
- If timestamp is `None`, use current UTC time.
- Return timezone-aware UTC datetime.

---

```python
def _validate_account_owner_name(
    self,
    owner_name: str,
) -> None
```

---

```python
def _validate_positive_amount(
    self,
    amount: Decimal,
    field_name: str,
) -> None
```

---

```python
def _validate_non_negative_amount(
    self,
    amount: Decimal,
    field_name: str,
) -> None
```

---

```python
def _validate_positive_quantity(
    self,
    quantity: Decimal,
) -> None
```

---

```python
def _normalize_symbol(
    self,
    symbol: str,
) -> str
```

---

```python
def _filter_transactions_as_of(
    self,
    transactions: list[Transaction],
    as_of: datetime | None,
) -> list[Transaction]
```

---

```python
def _sort_transactions(
    self,
    transactions: list[Transaction],
) -> list[Transaction]
```

---

```python
def _calculate_cash_balance_from_transactions(
    self,
    transactions: list[Transaction],
) -> Decimal
```

---

```python
def _calculate_holdings_from_transactions(
    self,
    transactions: list[Transaction],
) -> dict[str, Decimal]
```

---

```python
def _calculate_net_external_contributions_from_transactions(
    self,
    transactions: list[Transaction],
) -> Decimal
```

---

# 10. `formatters.py`

Pure helper functions for input parsing and UI formatting.

No business rules should be implemented here.

## 10.1 Input Parsing

```python
def decimal_from_user_number(
    value: int | float | str | Decimal | None,
    field_name: str,
) -> Decimal
```

Rules:

- Converts Gradio numeric/text input to `Decimal`.
- Raises `ValidationError` if missing or invalid.

---

```python
def parse_optional_datetime(
    value: str | None,
) -> datetime | None
```

Rules:

- Empty input returns `None`.
- ISO 8601 string returns timezone-aware datetime.
- Invalid string raises `ValidationError`.

Example accepted input:

```text
2024-01-01T10:30:00+00:00
```

---

## 10.2 Formatting

```python
def format_decimal_money(
    value: Decimal,
) -> str
```

---

```python
def format_decimal_quantity(
    value: Decimal,
) -> str
```

---

```python
def format_datetime(
    value: datetime | None,
) -> str
```

---

## 10.3 Table Formatting

```python
def accounts_to_dropdown_choices(
    accounts: list[Account],
) -> list[tuple[str, str]]
```

Returns Gradio dropdown choices:

```text
(label, value)
```

Example label:

```text
Alice — abc123
```

---

```python
def transactions_to_table(
    transactions: list[Transaction],
) -> list[list[str]]
```

Table columns:

```text
Sequence
Timestamp
Type
Symbol
Quantity
Execution Price
Cash Delta
Transaction ID
```

---

```python
def holdings_to_table(
    holdings: list[Holding],
) -> list[list[str]]
```

Table columns:

```text
Symbol
Quantity
```

---

```python
def valuation_to_positions_table(
    valuation: PortfolioValuation,
) -> list[list[str]]
```

Table columns:

```text
Symbol
Quantity
Price
Market Value
```

---

```python
def valuation_to_summary_markdown(
    valuation: PortfolioValuation,
) -> str
```

Should return markdown containing:

- Cash balance.
- Securities value.
- Total portfolio value.
- Net external contributions.
- Profit/loss.

---

# 11. `app.py`

Gradio frontend.

The app should use a single global in-memory service instance.

The app must only call `launch()` under a main guard so tests can import handler functions without starting the server.

---

## 11.1 Service Factory

```python
def build_service() -> AccountService
```

Creates:

- `InMemoryAccountRepository`
- `PriceService`
- `AccountService`

---

```python
def get_global_service() -> AccountService
```

Returns the global service instance.

---

## 11.2 Frontend Handler Methods

Handlers should:

- Validate required account selection.
- Convert user input using formatter helpers.
- Call backend service methods.
- Catch `TradingAppError`.
- Return safe user-readable messages.
- Never expose stack traces.

---

## 11.3 Account Handlers

```python
def handle_create_account(
    owner_name: str,
    initial_deposit: int | float | None,
) -> tuple[str, object]
```

Returns:

1. Status markdown.
2. Account dropdown update.

---

```python
def handle_refresh_accounts() -> tuple[object, str]
```

Returns:

1. Account dropdown update.
2. Status markdown.

---

## 11.4 Cash Handlers

```python
def handle_deposit(
    account_id: str | None,
    amount: int | float | None,
) -> str
```

Returns status markdown.

---

```python
def handle_withdraw(
    account_id: str | None,
    amount: int | float | None,
) -> str
```

Returns status markdown.

---

## 11.5 Trading Handlers

```python
def handle_buy(
    account_id: str | None,
    symbol: str | None,
    quantity: int | float | None,
) -> str
```

Returns status markdown.

---

```python
def handle_sell(
    account_id: str | None,
    symbol: str | None,
    quantity: int | float | None,
) -> str
```

Returns status markdown.

---

## 11.6 Reporting Handlers

```python
def handle_show_holdings(
    account_id: str | None,
    as_of_text: str | None,
) -> tuple[str, list[list[str]]]
```

Returns:

1. Status markdown.
2. Holdings table rows.

---

```python
def handle_show_valuation(
    account_id: str | None,
    as_of_text: str | None,
) -> tuple[str, list[list[str]], str]
```

Returns:

1. Status markdown.
2. Position valuation table rows.
3. Valuation summary markdown.

---

```python
def handle_show_transactions(
    account_id: str | None,
    start_time_text: str | None,
    end_time_text: str | None,
) -> tuple[str, list[list[str]]]
```

Returns:

1. Status markdown.
2. Transaction table rows.

---

# 12. Gradio UI Layout

Use `gr.Blocks`.

Do not use deprecated Gradio APIs such as:

```text
gr.inputs.*
gr.outputs.*
component.style(...)
```

---

## 12.1 Page Header

Markdown:

```text
# Trading Simulation Account Manager

Create accounts, manage cash, trade shares, and review point-in-time holdings and P&L.
```

---

## 12.2 Shared Account Selector

Components:

```python
account_dropdown = gr.Dropdown(
    label="Account",
    choices=[],
    interactive=True,
    allow_custom_value=False,
)
```

```python
refresh_accounts_button = gr.Button(value="Refresh Accounts")
```

---

## 12.3 Tab: Create Account

Components:

```python
owner_name_input = gr.Textbox(
    label="Owner Name",
    placeholder="Jane Trader",
)
```

```python
initial_deposit_input = gr.Number(
    label="Initial Deposit",
)
```

```python
create_account_button = gr.Button(value="Create Account")
```

```python
create_account_status = gr.Markdown(value="")
```

Event:

```python
create_account_button.click(
    fn=handle_create_account,
    inputs=[owner_name_input, initial_deposit_input],
    outputs=[create_account_status, account_dropdown],
    api_name="create_account",
)
```

---

## 12.4 Tab: Cash

Components:

```python
cash_amount_input = gr.Number(
    label="Amount",
)
```

```python
deposit_button = gr.Button(value="Deposit")
```

```python
withdraw_button = gr.Button(value="Withdraw")
```

```python
cash_status = gr.Markdown(value="")
```

Events:

```python
deposit_button.click(
    fn=handle_deposit,
    inputs=[account_dropdown, cash_amount_input],
    outputs=[cash_status],
    api_name="deposit",
)
```

```python
withdraw_button.click(
    fn=handle_withdraw,
    inputs=[account_dropdown, cash_amount_input],
    outputs=[cash_status],
    api_name="withdraw",
)
```

---

## 12.5 Tab: Trade

Components:

```python
symbol_dropdown = gr.Dropdown(
    label="Symbol",
    choices=["AAPL", "TSLA", "GOOGL"],
    interactive=True,
    allow_custom_value=False,
)
```

```python
trade_quantity_input = gr.Number(
    label="Quantity",
)
```

```python
buy_button = gr.Button(value="Buy")
```

```python
sell_button = gr.Button(value="Sell")
```

```python
trade_status = gr.Markdown(value="")
```

Events:

```python
buy_button.click(
    fn=handle_buy,
    inputs=[account_dropdown, symbol_dropdown, trade_quantity_input],
    outputs=[trade_status],
    api_name="buy",
)
```

```python
sell_button.click(
    fn=handle_sell,
    inputs=[account_dropdown, symbol_dropdown, trade_quantity_input],
    outputs=[trade_status],
    api_name="sell",
)
```

---

## 12.6 Tab: Holdings

Components:

```python
holdings_as_of_input = gr.Textbox(
    label="As Of Timestamp",
    placeholder="Optional ISO timestamp, e.g. 2024-01-01T10:30:00+00:00",
)
```

```python
show_holdings_button = gr.Button(value="Show Holdings")
```

```python
holdings_status = gr.Markdown(value="")
```

```python
holdings_table = gr.Dataframe(
    label="Holdings",
    headers=["Symbol", "Quantity"],
    datatype=["str", "str"],
    interactive=False,
)
```

Event:

```python
show_holdings_button.click(
    fn=handle_show_holdings,
    inputs=[account_dropdown, holdings_as_of_input],
    outputs=[holdings_status, holdings_table],
    api_name="show_holdings",
)
```

---

## 12.7 Tab: Valuation / P&L

Components:

```python
valuation_as_of_input = gr.Textbox(
    label="As Of Timestamp",
    placeholder="Optional ISO timestamp, e.g. 2024-01-01T10:30:00+00:00",
)
```

```python
show_valuation_button = gr.Button(value="Show Valuation / P&L")
```

```python
valuation_status = gr.Markdown(value="")
```

```python
positions_table = gr.Dataframe(
    label="Position Valuation",
    headers=["Symbol", "Quantity", "Price", "Market Value"],
    datatype=["str", "str", "str", "str"],
    interactive=False,
)
```

```python
valuation_summary = gr.Markdown(value="")
```

Event:

```python
show_valuation_button.click(
    fn=handle_show_valuation,
    inputs=[account_dropdown, valuation_as_of_input],
    outputs=[valuation_status, positions_table, valuation_summary],
    api_name="show_valuation",
)
```

---

## 12.8 Tab: Transactions

Components:

```python
transactions_start_input = gr.Textbox(
    label="Start Time",
    placeholder="Optional ISO timestamp",
)
```

```python
transactions_end_input = gr.Textbox(
    label="End Time",
    placeholder="Optional ISO timestamp",
)
```

```python
show_transactions_button = gr.Button(value="Show Transactions")
```

```python
transactions_status = gr.Markdown(value="")
```

```python
transactions_table = gr.Dataframe(
    label="Transactions",
    headers=[
        "Sequence",
        "Timestamp",
        "Type",
        "Symbol",
        "Quantity",
        "Execution Price",
        "Cash Delta",
        "Transaction ID",
    ],
    datatype=["str", "str", "str", "str", "str", "str", "str", "str"],
    interactive=False,
)
```

Event:

```python
show_transactions_button.click(
    fn=handle_show_transactions,
    inputs=[account_dropdown, transactions_start_input, transactions_end_input],
    outputs=[transactions_status, transactions_table],
    api_name="show_transactions",
)
```

---

# 13. Backend Behavior Examples

## 13.1 Create Account

Input:

```text
Owner: Alice
Initial deposit: 1000
```

Expected result:

```text
Account created.
Initial DEPOSIT transaction recorded.
Cash balance: 1000.00
Holdings: none
Profit/loss: 0.00
```

---

## 13.2 Buy Shares

Given:

```text
Cash: 1000.00
AAPL price: 150.00
Buy quantity: 2
```

Expected result:

```text
Buy cost: 300.00
Cash balance: 700.00
AAPL holdings: 2
BUY transaction recorded.
```

---

## 13.3 Reject Buy With Insufficient Funds

Given:

```text
Cash: 100.00
AAPL price: 150.00
Buy quantity: 1
```

Expected result:

```text
InsufficientFundsError raised.
No transaction recorded.
Cash unchanged.
Holdings unchanged.
```

---

## 13.4 Sell Shares

Given:

```text
AAPL holdings: 2
AAPL price: 150.00
Sell quantity: 1
```

Expected result:

```text
Sell proceeds: 150.00
Cash increases by 150.00
AAPL holdings: 1
SELL transaction recorded.
```

---

## 13.5 Reject Sell With Insufficient Holdings

Given:

```text
AAPL holdings: 1
Sell quantity: 2
```

Expected result:

```text
InsufficientHoldingsError raised.
No transaction recorded.
Cash unchanged.
Holdings unchanged.
```

---

# 14. Test Design

Use Python standard library `unittest`.

---

## 14.1 `test_price_service.py`

```python
class PriceServiceTests(unittest.TestCase):
    def test_get_share_price_supported_aapl(self) -> None

    def test_get_share_price_supported_tsla(self) -> None

    def test_get_share_price_supported_googl(self) -> None

    def test_get_price_normalizes_lowercase_symbol(self) -> None

    def test_get_price_unknown_symbol_raises(self) -> None

    def test_get_price_returns_decimal(self) -> None
```

---

## 14.2 `test_account_service.py`

### Account Creation Tests

```python
class AccountCreationTests(unittest.TestCase):
    def setUp(self) -> None

    def test_create_account_with_initial_deposit(self) -> None

    def test_create_account_with_zero_initial_deposit(self) -> None

    def test_create_account_rejects_negative_initial_deposit(self) -> None

    def test_create_account_rejects_blank_owner_name(self) -> None

    def test_list_accounts_returns_created_accounts(self) -> None
```

---

### Deposit Tests

```python
class DepositTests(unittest.TestCase):
    def setUp(self) -> None

    def test_deposit_increases_cash_balance(self) -> None

    def test_deposit_records_transaction(self) -> None

    def test_deposit_rejects_zero_amount(self) -> None

    def test_deposit_rejects_negative_amount(self) -> None

    def test_deposit_unknown_account_raises(self) -> None
```

---

### Withdrawal Tests

```python
class WithdrawalTests(unittest.TestCase):
    def setUp(self) -> None

    def test_withdraw_decreases_cash_balance(self) -> None

    def test_withdraw_records_transaction(self) -> None

    def test_withdraw_rejects_zero_amount(self) -> None

    def test_withdraw_rejects_negative_amount(self) -> None

    def test_withdraw_rejects_insufficient_funds(self) -> None

    def test_failed_withdraw_does_not_record_transaction(self) -> None
```

---

### Buy Tests

```python
class BuyTests(unittest.TestCase):
    def setUp(self) -> None

    def test_buy_decreases_cash_and_increases_holdings(self) -> None

    def test_buy_records_execution_price(self) -> None

    def test_buy_records_transaction(self) -> None

    def test_buy_rejects_insufficient_funds(self) -> None

    def test_failed_buy_does_not_record_transaction(self) -> None

    def test_buy_rejects_zero_quantity(self) -> None

    def test_buy_rejects_negative_quantity(self) -> None

    def test_buy_rejects_unknown_symbol(self) -> None
```

---

### Sell Tests

```python
class SellTests(unittest.TestCase):
    def setUp(self) -> None

    def test_sell_increases_cash_and_decreases_holdings(self) -> None

    def test_sell_records_execution_price(self) -> None

    def test_sell_records_transaction(self) -> None

    def test_sell_rejects_insufficient_holdings(self) -> None

    def test_failed_sell_does_not_record_transaction(self) -> None

    def test_sell_rejects_zero_quantity(self) -> None

    def test_sell_rejects_negative_quantity(self) -> None

    def test_sell_rejects_unknown_symbol(self) -> None
```

---

## 14.3 `test_point_in_time.py`

### Point-in-Time Holdings Tests

```python
class PointInTimeHoldingsTests(unittest.TestCase):
    def setUp(self) -> None

    def test_holdings_before_any_trades_are_empty(self) -> None

    def test_holdings_after_buy_include_symbol_quantity(self) -> None

    def test_holdings_between_buy_and_sell_include_pre_sell_quantity(self) -> None

    def test_holdings_after_sell_include_remaining_quantity(self) -> None

    def test_holdings_after_full_sell_omit_zero_quantity_symbol(self) -> None

    def test_as_of_includes_transactions_at_exact_timestamp(self) -> None
```

---

### Point-in-Time Cash Tests

```python
class PointInTimeCashTests(unittest.TestCase):
    def setUp(self) -> None

    def test_cash_before_initial_deposit_is_zero(self) -> None

    def test_cash_after_deposit(self) -> None

    def test_cash_after_buy(self) -> None

    def test_cash_between_buy_and_sell(self) -> None

    def test_cash_after_sell(self) -> None
```

---

### Point-in-Time Valuation Tests

```python
class PointInTimeValuationTests(unittest.TestCase):
    def setUp(self) -> None

    def test_portfolio_value_with_cash_only(self) -> None

    def test_portfolio_value_with_cash_and_holdings(self) -> None

    def test_profit_loss_zero_immediately_after_deposit(self) -> None

    def test_profit_loss_uses_net_external_contributions(self) -> None

    def test_profit_loss_after_withdrawal_is_not_artificial_loss(self) -> None

    def test_valuation_as_of_filters_later_transactions(self) -> None
```

---

## 14.4 `test_transactions.py`

```python
class TransactionListingTests(unittest.TestCase):
    def setUp(self) -> None

    def test_list_transactions_returns_all_in_sequence_order(self) -> None

    def test_list_transactions_filters_start_time(self) -> None

    def test_list_transactions_filters_end_time(self) -> None

    def test_list_transactions_filters_start_and_end_time(self) -> None

    def test_transaction_sequence_numbers_are_monotonic(self) -> None

    def test_transaction_ids_are_unique(self) -> None

    def test_failed_operations_do_not_create_transactions(self) -> None
```

---

## 14.5 `test_frontend_handlers.py`

Frontend tests should import handler functions from `app.py`.

They must not launch Gradio.

```python
class FrontendHandlerTests(unittest.TestCase):
    def setUp(self) -> None

    def test_create_account_handler_success(self) -> None

    def test_create_account_handler_validation_error(self) -> None

    def test_deposit_handler_requires_account(self) -> None

    def test_withdraw_handler_returns_error_for_insufficient_funds(self) -> None

    def test_buy_handler_returns_error_for_insufficient_funds(self) -> None

    def test_sell_handler_returns_error_for_insufficient_holdings(self) -> None

    def test_show_holdings_handler_returns_table_rows(self) -> None

    def test_show_transactions_handler_returns_table_rows(self) -> None

    def test_show_valuation_handler_returns_summary_markdown(self) -> None
```

---

# 15. Acceptance Criteria

The implementation is complete when:

1. A user can create an account.
2. A user can deposit funds.
3. A user can withdraw funds when cash is sufficient.
4. A withdrawal that would make cash negative is rejected.
5. A user can buy supported shares when cash is sufficient.
6. A buy that exceeds cash is rejected.
7. A user can sell shares when holdings are sufficient.
8. A sell that exceeds holdings is rejected.
9. Current holdings can be reported.
10. Holdings can be reported as of a timestamp.
11. Current profit/loss can be reported.
12. Profit/loss can be reported as of a timestamp.
13. Portfolio value can be reported.
14. Transactions can be listed over time.
15. Transactions can be filtered by start and end timestamp.
16. Failed operations do not create transactions.
17. All backend validation errors use domain-specific exceptions.
18. The Gradio frontend displays user-safe messages.
19. Unit tests pass using:

```text
uv run python -m unittest discover -s . -p "test_*.py"
```

20. All files are in the same directory.
21. No third-party dependencies are introduced beyond Gradio.