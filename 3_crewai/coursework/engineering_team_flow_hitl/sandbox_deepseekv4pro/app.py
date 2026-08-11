"""
app.py — Gradio frontend for the trading simulation account management system.

Provides a two-tier tab UI on top of the ``AccountManager`` backend from
``portfolio_manager.py``.
"""

from __future__ import annotations

import gradio as gr

from portfolio_manager import AccountManager


# ---------------------------------------------------------------------------
# Colour palette (works in light & dark mode via CSS variable fallbacks)
# ---------------------------------------------------------------------------

GOLD = "#ecad0a"
BLUE = "#209dd7"
PURPLE = "#753991"
GREEN = "#16a34a"
RED = "#dc2626"
GRAY_50 = "#f9fafb"
GRAY_800 = "#1f2937"
GRAY_700 = "#374151"
GRAY_300 = "#d1d5db"
GRAY_200 = "#e5e7eb"

# ---------------------------------------------------------------------------
# Custom CSS
# ---------------------------------------------------------------------------

CUSTOM_CSS = f"""
/* ---- Base resets ------------------------------------------------ */
body {{
    font-family: 'Inter', 'Segoe UI', system-ui, -apple-system, sans-serif;
}}

/* ---- Primary / secondary button overrides ----------------------- */
.gr-button-primary {{
    background-color: {BLUE} !important;
    border-color: {BLUE} !important;
    color: #ffffff !important;
}}

.gr-button-secondary {{
    border-color: {PURPLE} !important;
    color: {PURPLE} !important;
}}

/* ---- Tab navigation --------------------------------------------- */
.tabs > .tab-nav > button {{
    font-weight: 600 !important;
    font-size: 0.9rem !important;
    transition: all 0.15s ease;
}}

.tabs > .tab-nav > button.selected {{
    border-bottom: 3px solid {BLUE} !important;
}}

/* ---- Scrollable content areas ----------------------------------- */
.scrollable-content {{
    overflow-y: auto !important;
    max-height: 420px !important;
    padding-right: 6px !important;
}}

/* ---- Info card (used in profile summary etc.) ------------------- */
.info-card {{
    border: 1px solid var(--border-color-primary, {GRAY_200});
    border-radius: 12px;
    padding: 20px 24px;
    margin-bottom: 14px;
    background: var(--background-fill-secondary, {GRAY_50});
    box-shadow: 0 1px 3px rgba(0,0,0,0.06);
}}

/* ---- P&L colour helpers (light mode) ---------------------------- */
.profit-positive {{
    color: {GREEN} !important;
    font-weight: 700;
}}
.profit-negative {{
    color: {RED} !important;
    font-weight: 700;
}}

/* ---- Markdown table styling (holdings / transactions) ----------- */
.markdown-table {{
    width: 100%;
    border-collapse: collapse;
}}
.markdown-table th {{
    background: var(--background-fill-secondary, {GRAY_50});
    padding: 10px 14px;
    text-align: left;
    font-weight: 600;
    border-bottom: 2px solid var(--border-color-primary, {GRAY_300});
}}
.markdown-table td {{
    padding: 10px 14px;
    border-bottom: 1px solid var(--border-color-primary, {GRAY_200});
}}

/* ---- Dark-mode overrides ---------------------------------------- */
.dark .info-card {{
    background: var(--background-fill-secondary, {GRAY_800});
    border-color: var(--border-color-primary, {GRAY_700});
}}
.dark .profit-positive {{
    color: #4ade80 !important;
}}
.dark .profit-negative {{
    color: #f87171 !important;
}}
.dark .gr-button-secondary {{
    color: #c4b5fd !important;
    border-color: #a78bfa !important;
}}
"""

# ---------------------------------------------------------------------------
# Module-level helpers — build tab-population data
# ---------------------------------------------------------------------------


def _empty_lower_tabs():
    """Return a 15-tuple of default/empty ``gr.update`` values for every
    lower-tab display component."""
    return (
        gr.update(value="**Balance:** —"),               # 0  deposit_balance_display
        gr.update(value="**Balance:** —"),               # 1  withdraw_balance_display
        gr.update(value="**Current Price:** —"),          # 2  buy_price_display
        gr.update(value="**Estimated Total Cost:** —"),   # 3  buy_total_display
        gr.update(value="**Balance after purchase:** —"), # 4  buy_balance_display
        gr.update(value="**Current Price:** —"),          # 5  sell_price_display
        gr.update(value="**Your Holdings:** —"),          # 6  sell_holdings_display
        gr.update(value="**Balance after sale:** —"),     # 7  sell_balance_display
        gr.update(value="*No holdings yet.*"),             # 8  holdings_table
        gr.update(value="**Total Portfolio Value:** —"),  # 9  holdings_total_display
        gr.update(value="**Total Deposited:** —"),         # 10 pl_total_deposited
        gr.update(value="**Total Withdrawn:** —"),         # 11 pl_total_withdrawn
        gr.update(value="**Current Portfolio Value:** —"), # 12 pl_portfolio_value
        gr.update(value="**Net Profit / Loss:** —"),       # 13 pl_net
        gr.update(value="*No transactions yet.*"),         # 14 transactions_table
    )


def _populate_all_lower_tabs(account_id: str, mgr: AccountManager):
    """Return a 15-tuple of ``gr.update`` values fully populating every
    lower-tab display for the given *account_id*."""
    try:
        summary = mgr.get_account_summary(account_id)
    except KeyError:
        return _empty_lower_tabs()

    balance = summary["balance"]
    balance_str = f"**Balance:** ${balance:,.2f}"

    # ---- Holdings ---------------------------------------------------------
    holdings = summary["holdings"]
    total_holdings_value = 0.0

    if holdings:
        holdings_rows = [
            "| Symbol | Quantity | Current Price | Current Value |",
            "|--------|----------|---------------|---------------|",
        ]
        for sym, qty in sorted(holdings.items()):
            try:
                price = mgr.price_provider.get_share_price(sym)
            except ValueError:
                price = 0.0
            value = qty * price
            total_holdings_value += value
            holdings_rows.append(
                f"| {sym} | {qty} | ${price:,.2f} | ${value:,.2f} |"
            )
        holdings_md = "\n".join(holdings_rows)
        holdings_total_str = (
            f"**Total Portfolio Value:** ${total_holdings_value + balance:,.2f}"
        )
    else:
        holdings_md = "*No holdings yet.*"
        holdings_total_str = f"**Total Portfolio Value:** ${balance:,.2f}"

    # ---- Profit / Loss ----------------------------------------------------
    pl = summary["profit_loss"]
    pl_class = "profit-positive" if pl >= 0 else "profit-negative"
    pl_sign = "+" if pl >= 0 else ""
    pl_str = (
        f'<span class="{pl_class}">'
        f"**Net Profit / Loss:** {pl_sign}${pl:,.2f}"
        f"</span>"
    )

    # ---- Transactions -----------------------------------------------------
    txns = mgr.get_transactions(account_id)
    if txns:
        txn_rows = [
            "| Timestamp | Type | Symbol | Qty | Price | Amount |",
            "|-----------|------|--------|-----|-------|--------|",
        ]
        for t in txns:
            ts = t.timestamp.strftime("%Y-%m-%d %H:%M")
            ttype = t.transaction_type.value.capitalize()
            sym = t.symbol or "—"
            qty = str(t.quantity) if t.quantity is not None else "—"
            price = (
                f"${t.price_per_share:,.2f}"
                if t.price_per_share is not None
                else "—"
            )
            amt = f"${t.amount:,.2f}"
            txn_rows.append(
                f"| {ts} | {ttype} | {sym} | {qty} | {price} | {amt} |"
            )
        txn_md = "\n".join(txn_rows)
    else:
        txn_md = "*No transactions yet.*"

    # ---- Buy / Sell previews (AAPL as default) ----------------------------
    try:
        aapl_price = mgr.price_provider.get_share_price("AAPL")
        buy_price_str = f"**Current Price:** ${aapl_price:,.2f} per share"
        buy_total_str = (
            f"**Estimated Total Cost:** ${aapl_price:,.2f} (1 share)"
        )
    except ValueError:
        buy_price_str = "**Current Price:** —"
        buy_total_str = "**Estimated Total Cost:** —"

    try:
        aapl_price = mgr.price_provider.get_share_price("AAPL")
        sell_price_str = f"**Current Price:** ${aapl_price:,.2f} per share"
        held = holdings.get("AAPL", 0)
        sell_holdings_str = f"**Your Holdings:** {held} share(s) of AAPL"
    except ValueError:
        sell_price_str = "**Current Price:** —"
        sell_holdings_str = "**Your Holdings:** —"

    return (
        gr.update(value=balance_str),                                     # 0
        gr.update(value=balance_str),                                     # 1
        gr.update(value=buy_price_str),                                   # 2
        gr.update(value=buy_total_str),                                   # 3
        gr.update(value=f"**Balance after purchase:** ${balance:,.2f}"),  # 4
        gr.update(value=sell_price_str),                                  # 5
        gr.update(value=sell_holdings_str),                               # 6
        gr.update(value=f"**Balance after sale:** ${balance:,.2f}"),      # 7
        gr.update(value=holdings_md),                                     # 8
        gr.update(value=holdings_total_str),                              # 9
        gr.update(
            value=f"**Total Deposited:** ${summary['total_deposited']:,.2f}"
        ),                                                                # 10
        gr.update(
            value=f"**Total Withdrawn:** ${summary['total_withdrawn']:,.2f}"
        ),                                                                # 11
        gr.update(
            value=f"**Current Portfolio Value:** ${summary['portfolio_value']:,.2f}"
        ),                                                                # 12
        gr.update(value=pl_str),                                          # 13
        gr.update(value=txn_md),                                          # 14
    )


def _populate_profile_displays(account_id: str, mgr: AccountManager):
    """Return a 4-tuple of ``gr.update`` values for the profile-summary
    display fields."""
    try:
        summary = mgr.get_account_summary(account_id)
    except KeyError:
        return (
            gr.update(value="**Account:** —"),
            gr.update(value="**Balance:** —"),
            gr.update(value="**Holdings:** —"),
            gr.update(value="**P&L:** —"),
        )

    name = summary["name"]
    balance = summary["balance"]
    holdings_count = len(summary["holdings"])
    pl = summary["profit_loss"]

    pl_class = "profit-positive" if pl >= 0 else "profit-negative"
    pl_sign = "+" if pl >= 0 else ""

    return (
        gr.update(value=f"**Account:** {name}"),
        gr.update(value=f"**Balance:** ${balance:,.2f}"),
        gr.update(value=f"**Holdings:** {holdings_count} symbol(s)"),
        gr.update(
            value=(
                f'<span class="{pl_class}">'
                f"**P&L:** {pl_sign}${pl:,.2f}"
                f"</span>"
            )
        ),
    )


def _refresh_profile_state(mgr: AccountManager):
    """Return the six profile-state outputs corresponding to the current
    state of *mgr*.

    Returns
    -------
    (no_accounts_col, accounts_exist_col, profile_summary_col,
     account_dropdown, lower_tabs_container, selected_account_id)
    """
    accounts = mgr.list_accounts()
    if not accounts:
        return (
            gr.update(visible=True),         # no_accounts_col
            gr.update(visible=False),        # accounts_exist_col
            gr.update(visible=False),        # profile_summary_col
            gr.update(choices=[], value=None),  # account_dropdown
            gr.update(visible=False),        # lower_tabs_container
            None,                            # selected_account_id
        )
    choices = [
        (f"{a.name}  ({a.account_id[:8]}…)", a.account_id) for a in accounts
    ]
    return (
        gr.update(visible=False),            # no_accounts_col
        gr.update(visible=True),             # accounts_exist_col
        gr.update(visible=False),            # profile_summary_col
        gr.update(choices=choices, value=None),  # account_dropdown
        gr.update(visible=False),            # lower_tabs_container
        None,                                # selected_account_id
    )


# ---------------------------------------------------------------------------
# TradingSimulationApp
# ---------------------------------------------------------------------------


class TradingSimulationApp:
    """Gradio frontend for the AccountManager backend."""

    def __init__(self) -> None:
        self._manager = AccountManager()
        self._blocks = self.build()

    # -- build ---------------------------------------------------------------

    def build(self) -> gr.Blocks:
        """Construct and return the Gradio ``Blocks`` UI."""

        with gr.Blocks(title="📈 Trading Simulation") as blocks:

            # ================================================================
            # State
            # ================================================================
            selected_account_id = gr.State(value=None)
            account_manager = gr.State(value=self._manager)

            # ================================================================
            # Header
            # ================================================================
            gr.Markdown(
                "# 📈 Trading Simulation",
                elem_id="app-header",
            )
            gr.Markdown(
                "Deposit, withdraw, buy & sell shares, and track "
                "your simulated portfolio performance."
            )

            # ================================================================
            # UPPER TAB ROW  (always visible)
            # ================================================================
            with gr.Tabs(elem_classes="tabs"):

                # -- Profile Tab --------------------------------------------
                with gr.TabItem("👤 Profile", id="tab-profile"):

                    # State A: No accounts exist
                    with gr.Column(visible=True) as no_accounts_col:
                        gr.Markdown(
                            "### 📭 No accounts yet\n\n"
                            "Create one using the **🆕 Create New Account** "
                            "tab."
                        )

                    # State B / C: Accounts exist
                    with gr.Column(visible=False) as accounts_exist_col:
                        with gr.Row():
                            account_dropdown = gr.Dropdown(
                                label="Select Account",
                                choices=[],
                                interactive=True,
                                scale=4,
                            )
                            select_btn = gr.Button(
                                "🔍 Select Account",
                                variant="primary",
                                scale=1,
                            )

                    # State C: Account selected — summary
                    with gr.Column(visible=False) as profile_summary_col:
                        gr.Markdown("### 📋 Account Summary")
                        account_name_display = gr.Markdown("**Account:** —")
                        account_balance_display = gr.Markdown(
                            "**Balance:** —"
                        )
                        account_holdings_count_display = gr.Markdown(
                            "**Holdings:** —"
                        )
                        account_pl_display = gr.Markdown("**P&L:** —")

                # -- Create New Account Tab ---------------------------------
                with gr.TabItem("🆕 Create New Account", id="tab-create"):
                    with gr.Column():
                        gr.Markdown("### ✨ Create a New Trading Account")
                        new_account_name = gr.Textbox(
                            label="Account Name",
                            placeholder="e.g. My Growth Portfolio",
                        )
                        new_account_deposit = gr.Number(
                            label="Initial Deposit ($)",
                            value=1000.0,
                            minimum=0.0,
                            precision=2,
                        )
                        create_account_btn = gr.Button(
                            "✨ Create Account",
                            variant="primary",
                        )
                        create_account_msg = gr.Markdown(visible=False)

            # ================================================================
            # LOWER TAB ROW  (visible only when an account is selected)
            # ================================================================
            with gr.Column(visible=False) as lower_tabs_container:
                gr.Markdown("---")
                with gr.Tabs(elem_classes="tabs"):

                    # -- Deposit --------------------------------------------
                    with gr.TabItem("💰 Deposit", id="tab-deposit"):
                        with gr.Column():
                            deposit_amount = gr.Number(
                                label="Amount ($)",
                                value=100.0,
                                minimum=0.01,
                                precision=2,
                            )
                            deposit_btn = gr.Button(
                                "💰 Deposit Funds",
                                variant="primary",
                            )
                            deposit_balance_display = gr.Markdown(
                                "**Balance:** —"
                            )
                            deposit_feedback = gr.Markdown(visible=False)

                    # -- Withdraw -------------------------------------------
                    with gr.TabItem("🏦 Withdraw", id="tab-withdraw"):
                        with gr.Column():
                            withdraw_amount = gr.Number(
                                label="Amount ($)",
                                value=50.0,
                                minimum=0.01,
                                precision=2,
                            )
                            withdraw_btn = gr.Button(
                                "🏦 Withdraw Funds",
                                variant="secondary",
                            )
                            withdraw_balance_display = gr.Markdown(
                                "**Balance:** —"
                            )
                            withdraw_error = gr.Markdown(visible=False)

                    # -- Buy Shares -----------------------------------------
                    with gr.TabItem("📈 Buy Shares", id="tab-buy"):
                        with gr.Column():
                            with gr.Row():
                                buy_symbol = gr.Dropdown(
                                    label="Symbol",
                                    choices=["AAPL", "TSLA", "GOOGL"],
                                    value="AAPL",
                                    scale=2,
                                )
                                buy_quantity = gr.Number(
                                    label="Quantity",
                                    value=1,
                                    minimum=1,
                                    precision=0,
                                    scale=1,
                                )
                            buy_price_display = gr.Markdown(
                                "**Current Price:** —"
                            )
                            buy_total_display = gr.Markdown(
                                "**Estimated Total Cost:** —"
                            )
                            buy_btn = gr.Button(
                                "📈 Buy Shares",
                                variant="primary",
                            )
                            buy_balance_display = gr.Markdown(
                                "**Balance after purchase:** —"
                            )
                            buy_error = gr.Markdown(visible=False)

                    # -- Sell Shares ----------------------------------------
                    with gr.TabItem("📉 Sell Shares", id="tab-sell"):
                        with gr.Column():
                            with gr.Row():
                                sell_symbol = gr.Dropdown(
                                    label="Symbol",
                                    choices=["AAPL", "TSLA", "GOOGL"],
                                    value="AAPL",
                                    scale=2,
                                )
                                sell_quantity = gr.Number(
                                    label="Quantity",
                                    value=1,
                                    minimum=1,
                                    precision=0,
                                    scale=1,
                                )
                            sell_price_display = gr.Markdown(
                                "**Current Price:** —"
                            )
                            sell_holdings_display = gr.Markdown(
                                "**Your Holdings:** —"
                            )
                            sell_btn = gr.Button(
                                "📉 Sell Shares",
                                variant="secondary",
                            )
                            sell_balance_display = gr.Markdown(
                                "**Balance after sale:** —"
                            )
                            sell_error = gr.Markdown(visible=False)

                    # -- Holdings -------------------------------------------
                    with gr.TabItem("📦 Holdings", id="tab-holdings"):
                        holdings_table = gr.Markdown(
                            "*No holdings yet.*",
                            elem_classes="scrollable-content",
                        )
                        holdings_total_display = gr.Markdown(
                            "**Total Portfolio Value:** —"
                        )

                    # -- Profit / Loss --------------------------------------
                    with gr.TabItem("📊 Profit / Loss", id="tab-pl"):
                        pl_total_deposited = gr.Markdown(
                            "**Total Deposited:** —"
                        )
                        pl_total_withdrawn = gr.Markdown(
                            "**Total Withdrawn:** —"
                        )
                        pl_portfolio_value = gr.Markdown(
                            "**Current Portfolio Value:** —"
                        )
                        pl_net = gr.Markdown("**Net Profit / Loss:** —")

                    # -- Transactions ---------------------------------------
                    with gr.TabItem("📋 Transactions", id="tab-transactions"):
                        with gr.Row():
                            trans_type_filter = gr.Dropdown(
                                label="Filter by Type",
                                choices=[
                                    "All",
                                    "deposit",
                                    "withdraw",
                                    "buy",
                                    "sell",
                                ],
                                value="All",
                                scale=2,
                            )
                            trans_symbol_filter = gr.Dropdown(
                                label="Filter by Symbol",
                                choices=["All", "AAPL", "TSLA", "GOOGL"],
                                value="All",
                                scale=2,
                            )
                        transactions_table = gr.Markdown(
                            "*No transactions yet.*",
                            elem_classes="scrollable-content",
                        )

            # ================================================================
            # Named tuples of components for easy output wiring
            # ================================================================

            # The 15 lower-tab display fields (index-aligned with
            # _populate_all_lower_tabs / _empty_lower_tabs):
            _LOWER_TAB_FIELDS = [
                deposit_balance_display,      # 0
                withdraw_balance_display,     # 1
                buy_price_display,            # 2
                buy_total_display,            # 3
                buy_balance_display,          # 4
                sell_price_display,           # 5
                sell_holdings_display,        # 6
                sell_balance_display,         # 7
                holdings_table,               # 8
                holdings_total_display,       # 9
                pl_total_deposited,           # 10
                pl_total_withdrawn,           # 11
                pl_portfolio_value,           # 12
                pl_net,                       # 13
                transactions_table,           # 14
            ]

            # The 4 profile-summary display fields:
            _PROFILE_DISPLAY_FIELDS = [
                account_name_display,
                account_balance_display,
                account_holdings_count_display,
                account_pl_display,
            ]

            # The 4 per-action feedback/error messages (cleared on switch):
            _FEEDBACK_FIELDS = [
                deposit_feedback,
                withdraw_error,
                buy_error,
                sell_error,
            ]

            # ================================================================
            # Helper: safely convert a numeric input (handles None / empty)
            # ================================================================
            def _safe_float(value, field_name="Value"):
                """Convert *value* to float, raising a user-friendly
                ``ValueError`` if *value* is ``None`` or not numeric."""
                if value is None:
                    raise ValueError(f"{field_name} is required.")
                try:
                    return float(value)
                except (TypeError, ValueError):
                    raise ValueError(f"{field_name} must be a valid number.")

            def _safe_int(value, field_name="Value"):
                """Convert *value* to int, raising a user-friendly
                ``ValueError`` if *value* is ``None`` or not numeric."""
                if value is None:
                    raise ValueError(f"{field_name} is required.")
                try:
                    return int(value)
                except (TypeError, ValueError):
                    raise ValueError(f"{field_name} must be a valid integer.")

            # ================================================================
            # CALLBACK:  Create Account
            # ================================================================
            def _handle_create_account(name, deposit, mgr: AccountManager):
                # ── Validate deposit BEFORE anything else ──────────────────
                if deposit is None:
                    profile_state = _refresh_profile_state(mgr)
                    return (
                        gr.update(
                            visible=True,
                            value=(
                                "❌ **Error:** Initial deposit is required. "
                                "Please enter an amount (0 or greater)."
                            ),
                        ),
                        *profile_state[:-1],      # 5 profile outputs
                        gr.update(value=name or ""),   # preserve name
                        gr.update(value=1000.0),       # reset deposit
                    )

                try:
                    deposit_val = float(deposit)
                except (TypeError, ValueError):
                    profile_state = _refresh_profile_state(mgr)
                    return (
                        gr.update(
                            visible=True,
                            value=(
                                "❌ **Error:** Initial deposit must be a "
                                "valid number."
                            ),
                        ),
                        *profile_state[:-1],
                        gr.update(value=name or ""),
                        gr.update(value=1000.0),
                    )

                # ── Validate name ─────────────────────────────────────────
                if not name or not name.strip():
                    profile_state = _refresh_profile_state(mgr)
                    return (
                        gr.update(
                            visible=True,
                            value="❌ **Error:** Account name must not be "
                            "empty.",
                        ),
                        *profile_state[:-1],
                        gr.update(value=""),              # clear name
                        gr.update(value=deposit_val),     # preserve deposit
                    )

                # ── Duplicate name check ──────────────────────────────────
                name_stripped = name.strip()
                for acct in mgr.list_accounts():
                    if acct.name.lower() == name_stripped.lower():
                        profile_state = _refresh_profile_state(mgr)
                        return (
                            gr.update(
                                visible=True,
                                value=(
                                    f"❌ **Error:** An account with the name "
                                    f"'**{name_stripped}**' already exists. "
                                    "Please choose a different name."
                                ),
                            ),
                            *profile_state[:-1],
                            gr.update(value=""),          # clear name
                            gr.update(value=deposit_val), # preserve deposit
                        )

                # ── Create the account ────────────────────────────────────
                try:
                    mgr.create_account(name_stripped, deposit_val)
                    msg = (
                        f"✅ **Account '{name_stripped}' created "
                        f"successfully!** "
                        f"Go to the **👤 Profile** tab to select it."
                    )
                except (ValueError, KeyError) as e:
                    msg = f"❌ **Error:** {e}"

                profile_state = _refresh_profile_state(mgr)
                return (
                    gr.update(visible=True, value=msg),
                    *profile_state[:-1],          # 5 profile outputs
                    gr.update(value=""),          # clear name
                    gr.update(value=1000.0),      # reset deposit
                )

            create_account_btn.click(
                _handle_create_account,
                inputs=[
                    new_account_name,
                    new_account_deposit,
                    account_manager,
                ],
                outputs=[
                    create_account_msg,
                    no_accounts_col,
                    accounts_exist_col,
                    profile_summary_col,
                    account_dropdown,
                    lower_tabs_container,
                    new_account_name,
                    new_account_deposit,
                ],
            )

            # ================================================================
            # CALLBACK:  Select Account
            # ================================================================
            def _handle_select_account(account_id, mgr: AccountManager):
                if not account_id:
                    prof = _refresh_profile_state(mgr)
                    empty_4 = (
                        gr.update(value="**Account:** —"),
                        gr.update(value="**Balance:** —"),
                        gr.update(value="**Holdings:** —"),
                        gr.update(value="**P&L:** —"),
                    )
                    # Clear all feedback messages
                    cleared_fb = (
                        gr.update(visible=False, value=""),
                        gr.update(visible=False, value=""),
                        gr.update(visible=False, value=""),
                        gr.update(visible=False, value=""),
                    )
                    return (
                        prof                          # 6 profile state
                        + empty_4                     # 4 profile displays
                        + _empty_lower_tabs()          # 15 lower tabs
                        + cleared_fb                   # 4 feedbacks
                    )

                try:
                    summary = mgr.get_account_summary(account_id)
                except KeyError:
                    prof = _refresh_profile_state(mgr)
                    empty_4 = (
                        gr.update(value="**Account:** —"),
                        gr.update(value="**Balance:** —"),
                        gr.update(value="**Holdings:** —"),
                        gr.update(value="**P&L:** —"),
                    )
                    cleared_fb = (
                        gr.update(visible=False, value=""),
                        gr.update(visible=False, value=""),
                        gr.update(visible=False, value=""),
                        gr.update(visible=False, value=""),
                    )
                    return (
                        prof
                        + empty_4
                        + _empty_lower_tabs()
                        + cleared_fb
                    )

                # Profile-state tuple (6 items)
                profile_state = (
                    gr.update(visible=False),     # no_accounts_col
                    gr.update(visible=True),      # accounts_exist_col
                    gr.update(visible=True),      # profile_summary_col
                    gr.update(),                  # account_dropdown (keep)
                    gr.update(visible=True),      # lower_tabs_container
                    account_id,                   # selected_account_id
                )

                # Profile-summary displays (4 items)
                profile_displays = _populate_profile_displays(
                    account_id, mgr
                )

                # Populate lower tabs (15 items)
                lower = _populate_all_lower_tabs(account_id, mgr)

                # Clear all feedback messages (4 items)
                cleared_fb = (
                    gr.update(visible=False, value=""),
                    gr.update(visible=False, value=""),
                    gr.update(visible=False, value=""),
                    gr.update(visible=False, value=""),
                )

                return (
                    profile_state
                    + profile_displays
                    + lower
                    + cleared_fb
                )

            select_btn.click(
                _handle_select_account,
                inputs=[account_dropdown, account_manager],
                outputs=[
                    no_accounts_col,
                    accounts_exist_col,
                    profile_summary_col,
                    account_dropdown,
                    lower_tabs_container,
                    selected_account_id,
                    *_PROFILE_DISPLAY_FIELDS,
                    *_LOWER_TAB_FIELDS,
                    *_FEEDBACK_FIELDS,
                ],
            )

            # ================================================================
            # CALLBACK:  Deposit  (refreshes ALL lower-tab displays)
            # ================================================================
            def _handle_deposit(account_id, amount, mgr: AccountManager):
                if not account_id:
                    return (
                        gr.update(
                            visible=True,
                            value="❌ No account selected.",
                        ),
                    ) + _empty_lower_tabs()

                try:
                    amount_val = _safe_float(amount, "Deposit amount")
                except ValueError as e:
                    return (
                        gr.update(visible=True, value=f"❌ **Error:** {e}"),
                    ) + _populate_all_lower_tabs(account_id, mgr)

                try:
                    mgr.deposit(account_id, amount_val)
                    return (
                        gr.update(
                            visible=True,
                            value=(
                                f"✅ Deposited **${amount_val:,.2f}**."
                            ),
                        ),
                    ) + _populate_all_lower_tabs(account_id, mgr)
                except (ValueError, KeyError) as e:
                    return (
                        gr.update(
                            visible=True,
                            value=f"❌ **Error:** {e}",
                        ),
                    ) + _populate_all_lower_tabs(account_id, mgr)

            deposit_btn.click(
                _handle_deposit,
                inputs=[
                    selected_account_id,
                    deposit_amount,
                    account_manager,
                ],
                outputs=[deposit_feedback, *_LOWER_TAB_FIELDS],
            )

            # ================================================================
            # CALLBACK:  Withdraw  (refreshes ALL lower-tab displays)
            # ================================================================
            def _handle_withdraw(account_id, amount, mgr: AccountManager):
                if not account_id:
                    return (
                        gr.update(
                            visible=True,
                            value="❌ No account selected.",
                        ),
                    ) + _empty_lower_tabs()

                try:
                    amount_val = _safe_float(amount, "Withdrawal amount")
                except ValueError as e:
                    return (
                        gr.update(visible=True, value=f"❌ **Error:** {e}"),
                    ) + _populate_all_lower_tabs(account_id, mgr)

                try:
                    mgr.withdraw(account_id, amount_val)
                    return (
                        gr.update(
                            visible=True,
                            value=(
                                f"✅ Withdrew **${amount_val:,.2f}**."
                            ),
                        ),
                    ) + _populate_all_lower_tabs(account_id, mgr)
                except (ValueError, KeyError) as e:
                    return (
                        gr.update(
                            visible=True,
                            value=f"❌ **Error:** {e}",
                        ),
                    ) + _populate_all_lower_tabs(account_id, mgr)

            withdraw_btn.click(
                _handle_withdraw,
                inputs=[
                    selected_account_id,
                    withdraw_amount,
                    account_manager,
                ],
                outputs=[withdraw_error, *_LOWER_TAB_FIELDS],
            )

            # ================================================================
            # CALLBACK:  Buy Shares  (preview + execute)
            # ================================================================
            def _update_buy_preview(
                account_id, symbol, quantity, mgr: AccountManager
            ):
                if not account_id or not symbol:
                    return (
                        gr.update(value="**Current Price:** —"),
                        gr.update(value="**Estimated Total Cost:** —"),
                    )
                try:
                    price = mgr.price_provider.get_share_price(symbol)
                    qty = int(quantity) if quantity is not None else 1
                    total = price * qty
                    return (
                        gr.update(
                            value=f"**Current Price:** ${price:,.2f} "
                            "per share"
                        ),
                        gr.update(
                            value=f"**Estimated Total Cost:** ${total:,.2f}"
                        ),
                    )
                except ValueError:
                    return (
                        gr.update(
                            value="**Current Price:** Unknown symbol"
                        ),
                        gr.update(value="**Estimated Total Cost:** —"),
                    )

            for comp in (buy_symbol, buy_quantity):
                comp.change(
                    _update_buy_preview,
                    inputs=[
                        selected_account_id,
                        buy_symbol,
                        buy_quantity,
                        account_manager,
                    ],
                    outputs=[buy_price_display, buy_total_display],
                )

            def _handle_buy(
                account_id, symbol, quantity, mgr: AccountManager
            ):
                if not account_id:
                    return (
                        gr.update(
                            visible=True,
                            value="❌ No account selected.",
                        ),
                    ) + _empty_lower_tabs()

                try:
                    qty_val = _safe_int(quantity, "Quantity")
                except ValueError as e:
                    return (
                        gr.update(visible=True, value=f"❌ **Error:** {e}"),
                    ) + _populate_all_lower_tabs(account_id, mgr)

                try:
                    mgr.buy_shares(account_id, symbol, qty_val)
                    return (
                        gr.update(
                            visible=True,
                            value=(
                                f"✅ Bought **{qty_val} {symbol}**."
                            ),
                        ),
                    ) + _populate_all_lower_tabs(account_id, mgr)
                except (ValueError, KeyError) as e:
                    return (
                        gr.update(
                            visible=True,
                            value=f"❌ **Error:** {e}",
                        ),
                    ) + _populate_all_lower_tabs(account_id, mgr)

            buy_btn.click(
                _handle_buy,
                inputs=[
                    selected_account_id,
                    buy_symbol,
                    buy_quantity,
                    account_manager,
                ],
                outputs=[buy_error, *_LOWER_TAB_FIELDS],
            )

            # ================================================================
            # CALLBACK:  Sell Shares  (preview + execute)
            # ================================================================
            def _update_sell_preview(
                account_id, symbol, quantity, mgr: AccountManager
            ):
                if not account_id or not symbol:
                    return (
                        gr.update(value="**Current Price:** —"),
                        gr.update(value="**Your Holdings:** —"),
                    )
                try:
                    price = mgr.price_provider.get_share_price(symbol)
                    holdings = mgr.get_holdings(account_id)
                    held = holdings.get(symbol.upper(), 0)
                    return (
                        gr.update(
                            value=f"**Current Price:** ${price:,.2f} "
                            "per share"
                        ),
                        gr.update(
                            value=f"**Your Holdings:** {held} share(s) "
                            f"of {symbol}"
                        ),
                    )
                except ValueError:
                    return (
                        gr.update(
                            value="**Current Price:** Unknown symbol"
                        ),
                        gr.update(value="**Your Holdings:** —"),
                    )

            for comp in (sell_symbol, sell_quantity):
                comp.change(
                    _update_sell_preview,
                    inputs=[
                        selected_account_id,
                        sell_symbol,
                        sell_quantity,
                        account_manager,
                    ],
                    outputs=[sell_price_display, sell_holdings_display],
                )

            def _handle_sell(
                account_id, symbol, quantity, mgr: AccountManager
            ):
                if not account_id:
                    return (
                        gr.update(
                            visible=True,
                            value="❌ No account selected.",
                        ),
                    ) + _empty_lower_tabs()

                try:
                    qty_val = _safe_int(quantity, "Quantity")
                except ValueError as e:
                    return (
                        gr.update(visible=True, value=f"❌ **Error:** {e}"),
                    ) + _populate_all_lower_tabs(account_id, mgr)

                try:
                    mgr.sell_shares(account_id, symbol, qty_val)
                    return (
                        gr.update(
                            visible=True,
                            value=(
                                f"✅ Sold **{qty_val} {symbol}**."
                            ),
                        ),
                    ) + _populate_all_lower_tabs(account_id, mgr)
                except (ValueError, KeyError) as e:
                    return (
                        gr.update(
                            visible=True,
                            value=f"❌ **Error:** {e}",
                        ),
                    ) + _populate_all_lower_tabs(account_id, mgr)

            sell_btn.click(
                _handle_sell,
                inputs=[
                    selected_account_id,
                    sell_symbol,
                    sell_quantity,
                    account_manager,
                ],
                outputs=[sell_error, *_LOWER_TAB_FIELDS],
            )

            # ================================================================
            # CALLBACK:  Transactions filter
            # ================================================================
            def _render_transactions(
                account_id, type_filter, symbol_filter, mgr: AccountManager
            ):
                if not account_id:
                    return gr.update(value="*No transactions yet.*")

                txns = mgr.get_transactions(account_id)
                if not txns:
                    return gr.update(value="*No transactions yet.*")

                if type_filter and type_filter != "All":
                    txns = [
                        t
                        for t in txns
                        if t.transaction_type.value == type_filter
                    ]
                if symbol_filter and symbol_filter != "All":
                    txns = [
                        t
                        for t in txns
                        if t.symbol
                        and t.symbol.upper() == symbol_filter.upper()
                    ]

                if not txns:
                    return gr.update(value="*No matching transactions.*")

                rows = [
                    "| Timestamp | Type | Symbol | Qty | Price | Amount |",
                    "|-----------|------|--------|-----|-------|--------|",
                ]
                for t in txns:
                    ts = t.timestamp.strftime("%Y-%m-%d %H:%M")
                    ttype = t.transaction_type.value.capitalize()
                    sym = t.symbol or "—"
                    qty = str(t.quantity) if t.quantity is not None else "—"
                    price = (
                        f"${t.price_per_share:,.2f}"
                        if t.price_per_share is not None
                        else "—"
                    )
                    amt = f"${t.amount:,.2f}"
                    rows.append(
                        f"| {ts} | {ttype} | {sym} | {qty} | {price} "
                        f"| {amt} |"
                    )

                return gr.update(value="\n".join(rows))

            trans_type_filter.change(
                _render_transactions,
                inputs=[
                    selected_account_id,
                    trans_type_filter,
                    trans_symbol_filter,
                    account_manager,
                ],
                outputs=[transactions_table],
            )
            trans_symbol_filter.change(
                _render_transactions,
                inputs=[
                    selected_account_id,
                    trans_type_filter,
                    trans_symbol_filter,
                    account_manager,
                ],
                outputs=[transactions_table],
            )

            # ================================================================
            # INITIAL LOAD
            # ================================================================
            blocks.load(
                _refresh_profile_state,
                inputs=[account_manager],
                outputs=[
                    no_accounts_col,
                    accounts_exist_col,
                    profile_summary_col,
                    account_dropdown,
                    lower_tabs_container,
                    selected_account_id,
                ],
            )

        return blocks

    # -- launch --------------------------------------------------------------

    def launch(self, **kwargs) -> None:
        """Launch the Gradio app with the Soft theme and dark mode support."""
        kwargs.setdefault("theme", gr.themes.Soft())
        kwargs.setdefault("css", CUSTOM_CSS)
        self._blocks.launch(**kwargs)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    app = TradingSimulationApp()
    app.launch()
