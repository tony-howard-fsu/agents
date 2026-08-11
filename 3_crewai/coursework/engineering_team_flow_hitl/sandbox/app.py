import gradio as gr
from backend import AccountManager, SharePriceService


# Module-level price service for trade symbol price lookups
_price_service = SharePriceService()


# ---------------------------------------------------------------------------
# Helper utilities
# ---------------------------------------------------------------------------

def _fmt_dollar(value: float) -> str:
    """Format a dollar amount with commas and 2 decimal places."""
    if value < 0:
        return f"-${abs(value):,.2f}"
    return f"${value:,.2f}"


def _build_account_choices(manager: AccountManager) -> list[tuple[str, str]]:
    """Build (label, id) tuples for the account dropdown."""
    return [
        (f"{a['name']} ({a['id'][:8]}...)", a["id"])
        for a in manager.list_accounts()
    ]


def _empty_holdings_data() -> list:
    """Return an empty holdings table value, forcing a DataFrame reset."""
    return []


def _empty_transactions_data() -> list:
    """Return an empty transactions table value, forcing a DataFrame reset."""
    return []


def refresh_profile_data(
    account_id: str, manager: AccountManager
) -> tuple[str, list, list, str]:
    """Return (info_md, holdings_data, transactions_data, pl_md) for an account."""
    if not account_id:
        return "", _empty_holdings_data(), _empty_transactions_data(), "No data"

    account_name = manager.get_account_name(account_id)
    balance = manager.get_balance(account_id)
    info_md = f"**Account:** {account_name}  |  **Balance:** {_fmt_dollar(balance)}"

    # Holdings table rows
    holdings_data: list[list] = []
    for h in manager.get_holdings_with_market_value(account_id):
        holdings_data.append([
            h["symbol"],
            h["quantity"],
            _fmt_dollar(h["avg_cost"]),
            _fmt_dollar(h["current_price"]),
            _fmt_dollar(h["market_value"]),
            _fmt_dollar(h["unrealized_pl"]),
        ])

    # Transactions table rows (most recent first)
    transactions_data: list[list] = []
    for tx in manager.get_transactions(account_id):
        transactions_data.append([
            tx.timestamp.strftime("%Y-%m-%d %H:%M:%S"),
            tx.type,
            tx.symbol if tx.symbol else "-",
            tx.quantity if tx.quantity is not None else "-",
            _fmt_dollar(tx.price) if tx.price is not None else "-",
            _fmt_dollar(tx.amount),
        ])

    # P&L
    pl = manager.get_profit_loss(account_id)
    pl_color = "green" if pl >= 0 else "red"
    pl_md = (
        f"### Profit / Loss:&nbsp;&nbsp;"
        f"<span style='color:{pl_color};font-size:1.2em'>{_fmt_dollar(pl)}</span>"
    )

    return info_md, holdings_data, transactions_data, pl_md


# ---------------------------------------------------------------------------
# Event handlers
# ---------------------------------------------------------------------------

def handle_create_account(
    name: str, initial_deposit: float, manager: AccountManager
) -> tuple[str, dict]:
    """Validate and create a new account, then refresh the dropdown."""
    if initial_deposit is None:
        initial_deposit = 0.0

    if not name or not name.strip():
        choices = _build_account_choices(manager)
        return (
            "<span style='color:red'>❌ Account name must be non-empty.</span>",
            gr.update(choices=choices),
        )

    try:
        account_id = manager.create_account(name.strip(), initial_deposit)
        choices = _build_account_choices(manager)
        return (
            f"<span style='color:green'>✅ Account **'{name.strip()}'** created successfully!</span>",
            gr.update(choices=choices, value=account_id),
        )
    except ValueError as exc:
        choices = _build_account_choices(manager)
        return (
            f"<span style='color:red'>❌ {exc}</span>",
            gr.update(choices=choices),
        )


def handle_select_account(
    account_id: str, manager: AccountManager
) -> tuple:
    """Load an account and populate all profile sub-tabs.

    **All** status messages from action tabs are cleared to prevent
    stale feedback from a previously-loaded account.  Trade inputs
    (current price, estimated total) are also reset.
    """
    if not account_id:
        # No account selected → hide sub-tabs and clear everything
        return (
            "No accounts yet — go to ➕ Create Account tab.",
            gr.update(visible=False),
            gr.update(value=_empty_holdings_data()),
            gr.update(value=_empty_transactions_data()),
            "No data",
            gr.update(value="AAPL"),
            "",        # deposit_status  → cleared
            "",        # withdraw_status → cleared
            "",        # trade_status    → cleared
            0.0,       # current_price_display → reset
            0.0,       # trade_total           → reset
        )

    info_md, holdings_data, transactions_data, pl_md = refresh_profile_data(
        account_id, manager
    )
    return (
        info_md,
        gr.update(visible=True),
        gr.update(value=holdings_data),
        gr.update(value=transactions_data),
        pl_md,
        gr.update(value="AAPL"),
        "",        # deposit_status  → cleared
        "",        # withdraw_status → cleared
        "",        # trade_status    → cleared
        0.0,       # current_price_display → reset
        0.0,       # trade_total           → reset
    )


def handle_deposit(
    account_id: str, amount: float, manager: AccountManager
) -> tuple:
    """Deposit cash into the loaded account."""
    if not account_id:
        return (
            "<span style='color:red'>❌ No account selected.</span>",
            "",
            gr.update(value=_empty_holdings_data()),
            gr.update(value=_empty_transactions_data()),
            "No data",
        )

    try:
        manager.deposit(account_id, amount)
        info, holdings, transactions, pl = refresh_profile_data(account_id, manager)
        return (
            f"<span style='color:green'>✅ Deposited {_fmt_dollar(amount)} successfully!</span>",
            info,
            gr.update(value=holdings),
            gr.update(value=transactions),
            pl,
        )
    except (ValueError, KeyError) as exc:
        info, holdings, transactions, pl = refresh_profile_data(account_id, manager)
        return (
            f"<span style='color:red'>❌ {exc}</span>",
            info,
            gr.update(value=holdings),
            gr.update(value=transactions),
            pl,
        )


def handle_withdraw(
    account_id: str, amount: float, manager: AccountManager
) -> tuple:
    """Withdraw cash from the loaded account."""
    if not account_id:
        return (
            "<span style='color:red'>❌ No account selected.</span>",
            "",
            gr.update(value=_empty_holdings_data()),
            gr.update(value=_empty_transactions_data()),
            "No data",
        )

    try:
        manager.withdraw(account_id, amount)
        info, holdings, transactions, pl = refresh_profile_data(account_id, manager)
        return (
            f"<span style='color:green'>✅ Withdrew {_fmt_dollar(amount)} successfully!</span>",
            info,
            gr.update(value=holdings),
            gr.update(value=transactions),
            pl,
        )
    except (ValueError, KeyError) as exc:
        info, holdings, transactions, pl = refresh_profile_data(account_id, manager)
        return (
            f"<span style='color:red'>❌ {exc}</span>",
            info,
            gr.update(value=holdings),
            gr.update(value=transactions),
            pl,
        )


def handle_buy(
    account_id: str, symbol: str, quantity: float, manager: AccountManager
) -> tuple:
    """Buy shares in the loaded account."""
    if not account_id:
        return (
            "<span style='color:red'>❌ No account selected.</span>",
            "",
            gr.update(value=_empty_holdings_data()),
            gr.update(value=_empty_transactions_data()),
            "No data",
        )

    try:
        qty = int(quantity)
        manager.buy(account_id, symbol, qty)
        info, holdings, transactions, pl = refresh_profile_data(account_id, manager)
        return (
            f"<span style='color:green'>✅ Bought {qty} share(s) of **{symbol}**!</span>",
            info,
            gr.update(value=holdings),
            gr.update(value=transactions),
            pl,
        )
    except (ValueError, KeyError) as exc:
        info, holdings, transactions, pl = refresh_profile_data(account_id, manager)
        return (
            f"<span style='color:red'>❌ {exc}</span>",
            info,
            gr.update(value=holdings),
            gr.update(value=transactions),
            pl,
        )


def handle_sell(
    account_id: str, symbol: str, quantity: float, manager: AccountManager
) -> tuple:
    """Sell shares in the loaded account."""
    if not account_id:
        return (
            "<span style='color:red'>❌ No account selected.</span>",
            "",
            gr.update(value=_empty_holdings_data()),
            gr.update(value=_empty_transactions_data()),
            "No data",
        )

    try:
        qty = int(quantity)
        manager.sell(account_id, symbol, qty)
        info, holdings, transactions, pl = refresh_profile_data(account_id, manager)
        return (
            f"<span style='color:green'>✅ Sold {qty} share(s) of **{symbol}**!</span>",
            info,
            gr.update(value=holdings),
            gr.update(value=transactions),
            pl,
        )
    except (ValueError, KeyError) as exc:
        info, holdings, transactions, pl = refresh_profile_data(account_id, manager)
        return (
            f"<span style='color:red'>❌ {exc}</span>",
            info,
            gr.update(value=holdings),
            gr.update(value=transactions),
            pl,
        )


def handle_trade_symbol_change(symbol: str) -> tuple[float, float]:
    """Update the current-price display when the trade symbol changes.

    Uses the module-level _price_service directly — no AccountManager needed.
    """
    if not symbol:
        return 0.0, 0.0
    try:
        price = _price_service.get_share_price(symbol)
    except ValueError:
        price = 0.0
    return price, 0.0


def handle_trade_quantity_change(
    quantity: float, price: float
) -> float:
    """Update the estimated total when quantity changes."""
    if quantity is None or price is None:
        return 0.0
    return float(quantity) * float(price)


# ---------------------------------------------------------------------------
# UI definition
# ---------------------------------------------------------------------------

def create_ui() -> gr.Blocks:
    manager = AccountManager()

    with gr.Blocks(title="Trading Simulation") as app:
        state = gr.State(manager)

        with gr.Tabs() as top_tabs:
            # ===============================================================
            # 📋 Profile tab
            # ===============================================================
            with gr.Tab("📋 Profile", id="profile_tab"):
                gr.Markdown("## Account Profile")

                with gr.Row():
                    account_dropdown = gr.Dropdown(
                        label="Select Account",
                        choices=[],
                        interactive=True,
                        scale=3,
                    )
                    load_btn = gr.Button("Load Account", variant="primary", scale=1)

                account_info = gr.Markdown(
                    value="No accounts yet — go to ➕ Create Account tab."
                )

                # Sub-tabs — hidden until an account is loaded
                with gr.Tabs(visible=False) as sub_tabs:
                    # -- Deposit -------------------------------------------------
                    with gr.Tab("💵 Deposit"):
                        with gr.Row():
                            deposit_amount = gr.Number(
                                label="Amount ($)",
                                minimum=0.01,
                                value=0.01,
                            )
                            deposit_btn = gr.Button("Deposit", variant="primary")
                        deposit_status = gr.Markdown(visible=True)

                    # -- Withdraw ------------------------------------------------
                    with gr.Tab("🏦 Withdraw"):
                        with gr.Row():
                            withdraw_amount = gr.Number(
                                label="Amount ($)",
                                minimum=0.01,
                                value=0.01,
                            )
                            withdraw_btn = gr.Button("Withdraw", variant="stop")
                        withdraw_status = gr.Markdown(visible=True)

                    # -- Trade ---------------------------------------------------
                    with gr.Tab("📈 Trade"):
                        with gr.Row():
                            with gr.Column(scale=1):
                                trade_symbol = gr.Dropdown(
                                    label="Symbol",
                                    choices=["AAPL", "TSLA", "GOOGL"],
                                    value="AAPL",
                                )
                                trade_quantity = gr.Number(
                                    label="Quantity",
                                    minimum=1,
                                    precision=0,
                                    value=1,
                                )
                                current_price_display = gr.Number(
                                    label="Current Price ($)",
                                    interactive=False,
                                    value=0.0,
                                )
                            with gr.Column(scale=1):
                                trade_total = gr.Number(
                                    label="Estimated Total ($)",
                                    interactive=False,
                                    value=0.0,
                                )
                                with gr.Row():
                                    buy_btn = gr.Button("Buy", variant="primary")
                                    sell_btn = gr.Button("Sell", variant="stop")
                        trade_status = gr.Markdown(visible=True)

                    # -- Holdings -------------------------------------------------
                    with gr.Tab("📊 Holdings"):
                        holdings_table = gr.DataFrame(
                            headers=[
                                "Symbol",
                                "Quantity",
                                "Avg Cost",
                                "Current Price",
                                "Market Value",
                                "Unrealized P/L",
                            ],
                            interactive=False,
                            max_height=300,
                            value=_empty_holdings_data(),
                        )

                    # -- P&L -----------------------------------------------------
                    with gr.Tab("💰 P&L"):
                        pl_display = gr.Markdown(value="No data")

                    # -- Transactions --------------------------------------------
                    with gr.Tab("🧾 Transactions"):
                        transactions_table = gr.DataFrame(
                            headers=[
                                "Time",
                                "Type",
                                "Symbol",
                                "Quantity",
                                "Price",
                                "Amount",
                            ],
                            interactive=False,
                            max_height=300,
                            value=_empty_transactions_data(),
                        )

            # ===============================================================
            # ➕ Create Account tab
            # ===============================================================
            with gr.Tab("➕ Create Account", id="create_tab"):
                gr.Markdown("## Create a New Account")

                name_input = gr.Textbox(
                    label="Account Name",
                    placeholder="Enter name...",
                )
                deposit_input = gr.Number(
                    label="Initial Deposit ($)",
                    value=0.0,
                    minimum=0.0,
                )
                create_btn = gr.Button("Create Account", variant="primary")
                create_status = gr.Markdown(visible=True)

        # ------------------------------------------------------------------
        # Wire events
        # ------------------------------------------------------------------

        # Create account
        create_btn.click(
            fn=handle_create_account,
            inputs=[name_input, deposit_input, state],
            outputs=[create_status, account_dropdown],
        )

        # Load / select account — clears *every* status message and resets
        # trade inputs so nothing leaks from the previously viewed account.
        load_btn.click(
            fn=handle_select_account,
            inputs=[account_dropdown, state],
            outputs=[
                account_info,
                sub_tabs,
                holdings_table,
                transactions_table,
                pl_display,
                trade_symbol,
                deposit_status,
                withdraw_status,
                trade_status,
                current_price_display,
                trade_total,
            ],
        )

        # Deposit
        deposit_btn.click(
            fn=handle_deposit,
            inputs=[account_dropdown, deposit_amount, state],
            outputs=[
                deposit_status,
                account_info,
                holdings_table,
                transactions_table,
                pl_display,
            ],
        )

        # Withdraw
        withdraw_btn.click(
            fn=handle_withdraw,
            inputs=[account_dropdown, withdraw_amount, state],
            outputs=[
                withdraw_status,
                account_info,
                holdings_table,
                transactions_table,
                pl_display,
            ],
        )

        # Buy
        buy_btn.click(
            fn=handle_buy,
            inputs=[account_dropdown, trade_symbol, trade_quantity, state],
            outputs=[
                trade_status,
                account_info,
                holdings_table,
                transactions_table,
                pl_display,
            ],
        )

        # Sell
        sell_btn.click(
            fn=handle_sell,
            inputs=[account_dropdown, trade_symbol, trade_quantity, state],
            outputs=[
                trade_status,
                account_info,
                holdings_table,
                transactions_table,
                pl_display,
            ],
        )

        # Reactive: symbol change → price + reset total
        # Uses module-level _price_service, so no state needed
        trade_symbol.change(
            fn=handle_trade_symbol_change,
            inputs=[trade_symbol],
            outputs=[current_price_display, trade_total],
        )

        # Reactive: quantity change → recalc estimated total
        trade_quantity.change(
            fn=handle_trade_quantity_change,
            inputs=[trade_quantity, current_price_display],
            outputs=[trade_total],
        )

    return app


# ---------------------------------------------------------------------------
# Launch
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    theme = gr.themes.Soft(
        primary_hue=gr.themes.colors.blue,
        secondary_hue=gr.themes.colors.amber,
        neutral_hue=gr.themes.colors.slate,
    )
    app = create_ui()
    app.launch(theme=theme)
