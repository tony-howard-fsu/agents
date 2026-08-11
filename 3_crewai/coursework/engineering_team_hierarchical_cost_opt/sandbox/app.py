"""Gradio web interface for the Trading Simulation Account Management System."""

import gradio as gr
from backend import AccountManager, InsufficientFundsError, InsufficientSharesError

manager = AccountManager()

with gr.Blocks(title="Trading Simulation - Account Management") as app:
    gr.Markdown("# 📈 Trading Simulation - Account Management")

    account_state = gr.State(value=None)

    # ------------------------------------------------------------------
    # Section 1: Account Creation
    # ------------------------------------------------------------------
    gr.Markdown("## 1. Create Account")
    with gr.Row():
        initial_deposit_input = gr.Number(
            label="Initial Deposit ($)", value=0, minimum=0
        )
        create_btn = gr.Button("Create Account", variant="primary")
    account_id_display = gr.Textbox(label="Account ID", interactive=False)

    # ------------------------------------------------------------------
    # Section 2: Cash Operations
    # ------------------------------------------------------------------
    gr.Markdown("## 2. Cash Operations")
    with gr.Row():
        amount_input = gr.Number(label="Amount ($)", value=0, minimum=0.01)
        deposit_btn = gr.Button("Deposit")
        withdraw_btn = gr.Button("Withdraw")
    cash_status = gr.Textbox(label="Status", interactive=False)

    # ------------------------------------------------------------------
    # Section 3: Trade Recording
    # ------------------------------------------------------------------
    gr.Markdown("## 3. Trade Recording")
    with gr.Row():
        symbol_input = gr.Textbox(label="Stock Symbol (e.g., AAPL, TSLA, GOOGL)")
        quantity_input = gr.Number(label="Quantity", value=1, minimum=0)
        trade_type = gr.Radio(
            label="Trade Type", choices=["BUY", "SELL"], value="BUY"
        )
    trade_btn = gr.Button("Submit Trade", variant="primary")
    trade_status = gr.Textbox(label="Trade Status", interactive=False)

    # ------------------------------------------------------------------
    # Section 4: Reports
    # ------------------------------------------------------------------
    gr.Markdown("## 4. Reports")
    with gr.Row():
        portfolio_btn = gr.Button("Portfolio Value")
        pnl_btn = gr.Button("Profit / Loss")
    with gr.Row():
        portfolio_display = gr.Textbox(label="Portfolio Value", interactive=False)
        pnl_display = gr.Textbox(label="Profit / Loss", interactive=False)

    with gr.Row():
        holdings_btn = gr.Button("Show Holdings")
        history_btn = gr.Button("Transaction History")
    holdings_table = gr.Dataframe(
        headers=["Symbol", "Quantity"],
        label="Current Holdings",
    )
    history_table = gr.Dataframe(
        headers=["Timestamp", "Type", "Symbol", "Quantity", "Price", "Amount"],
        label="Transaction History",
    )

    # ==================================================================
    # Event Handler Functions
    # ==================================================================

    def handle_create_account(initial_deposit, current_state):
        """Create a new account and store its ID in state."""
        try:
            acc_id = manager.create_account(initial_deposit)
            return acc_id, acc_id
        except ValueError as e:
            return f"Error: {e}", current_state

    def handle_deposit(amount, current_state):
        """Deposit cash into the current account."""
        if current_state is None:
            return "Error: No account created yet. Please create one first.", current_state
        try:
            manager.deposit(current_state, amount)
            return f"✅ Successfully deposited ${amount:,.2f}.", current_state
        except (ValueError, KeyError) as e:
            return f"Error: {e}", current_state

    def handle_withdraw(amount, current_state):
        """Withdraw cash from the current account."""
        if current_state is None:
            return "Error: No account created yet. Please create one first.", current_state
        try:
            manager.withdraw(current_state, amount)
            return f"✅ Successfully withdrew ${amount:,.2f}.", current_state
        except InsufficientFundsError as e:
            return f"Error: Insufficient funds — {e}", current_state
        except (ValueError, KeyError) as e:
            return f"Error: {e}", current_state

    def handle_trade(symbol, quantity, trade_type_val, current_state):
        """Record a BUY or SELL trade."""
        if current_state is None:
            return "Error: No account created yet. Please create one first.", current_state
        if not symbol or not symbol.strip():
            return "Error: Please enter a stock symbol.", current_state
        try:
            symbol_clean = symbol.strip().upper()
            manager.record_trade(current_state, trade_type_val, symbol_clean, quantity)
            return (
                f"✅ Successfully executed {trade_type_val} of "
                f"{quantity} share(s) of {symbol_clean}.",
                current_state,
            )
        except InsufficientFundsError as e:
            return f"Error: Insufficient funds — {e}", current_state
        except InsufficientSharesError as e:
            return f"Error: Insufficient shares — {e}", current_state
        except (ValueError, KeyError) as e:
            return f"Error: {e}", current_state

    def handle_portfolio(current_state):
        """Return the current portfolio value."""
        if current_state is None:
            return "No account created yet."
        try:
            value = manager.get_portfolio_value(current_state)
            return f"${value:,.2f}"
        except (ValueError, KeyError) as e:
            return f"Error: {e}"

    def handle_pnl(current_state):
        """Return the current profit / loss."""
        if current_state is None:
            return "No account created yet."
        try:
            value = manager.get_profit_loss(current_state)
            return f"${value:,.2f}"
        except (ValueError, KeyError) as e:
            return f"Error: {e}"

    def handle_holdings(current_state):
        """Return a table of current holdings."""
        if current_state is None:
            return []
        try:
            holdings = manager.get_holdings_report(current_state)
            return [[h.symbol, h.quantity] for h in holdings]
        except (ValueError, KeyError):
            return []

    def handle_history(current_state):
        """Return the full transaction history table."""
        if current_state is None:
            return []
        try:
            txs = manager.get_transaction_history(current_state)
            return [
                [
                    t.timestamp.isoformat(),
                    t.type,
                    t.symbol,
                    t.quantity,
                    t.price,
                    t.amount,
                ]
                for t in txs
            ]
        except (ValueError, KeyError):
            return []

    # ==================================================================
    # Wire Events
    # ==================================================================

    create_btn.click(
        fn=handle_create_account,
        inputs=[initial_deposit_input, account_state],
        outputs=[account_id_display, account_state],
    )

    deposit_btn.click(
        fn=handle_deposit,
        inputs=[amount_input, account_state],
        outputs=[cash_status, account_state],
    )

    withdraw_btn.click(
        fn=handle_withdraw,
        inputs=[amount_input, account_state],
        outputs=[cash_status, account_state],
    )

    trade_btn.click(
        fn=handle_trade,
        inputs=[symbol_input, quantity_input, trade_type, account_state],
        outputs=[trade_status, account_state],
    )

    portfolio_btn.click(
        fn=handle_portfolio,
        inputs=[account_state],
        outputs=[portfolio_display],
    )

    pnl_btn.click(
        fn=handle_pnl,
        inputs=[account_state],
        outputs=[pnl_display],
    )

    holdings_btn.click(
        fn=handle_holdings,
        inputs=[account_state],
        outputs=[holdings_table],
    )

    history_btn.click(
        fn=handle_history,
        inputs=[account_state],
        outputs=[history_table],
    )

if __name__ == "__main__":
    app.launch()
