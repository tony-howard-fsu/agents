from __future__ import annotations

from typing import Any

from account_service import AccountService
from exceptions import TradingAppError, ValidationError
from formatters import (
    accounts_to_dropdown_choices,
    decimal_from_user_number,
    format_decimal_money,
    format_decimal_quantity,
    holdings_to_table,
    parse_optional_datetime,
    transactions_to_table,
    valuation_to_positions_table,
    valuation_to_summary_markdown,
)
from price_service import PriceService
from repository import InMemoryAccountRepository

try:
    import gradio as gr
except Exception:  # pragma: no cover
    class _Update(dict):
        pass

    class _DummyComponent:
        def __init__(self, *args, **kwargs):
            pass

        def click(self, *args, **kwargs):
            return self

    class _DummyCtx:
        def __init__(self, *args, **kwargs):
            pass

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

    class gr:  # type: ignore
        @staticmethod
        def update(**kwargs):
            return _Update(kwargs)

        Blocks = _DummyCtx
        Tab = _DummyCtx
        Row = _DummyCtx
        Column = _DummyCtx
        Markdown = Textbox = Number = Button = Dropdown = Dataframe = _DummyComponent

        class themes:  # type: ignore
            class Soft:
                def __init__(self, *args, **kwargs):
                    pass


_GLOBAL_SERVICE: AccountService | None = None


def build_service() -> AccountService:
    return AccountService(InMemoryAccountRepository(), PriceService())


def get_global_service() -> AccountService:
    global _GLOBAL_SERVICE
    if _GLOBAL_SERVICE is None:
        _GLOBAL_SERVICE = build_service()
    return _GLOBAL_SERVICE


def _safe_error_message(exc: Exception) -> str:
    return f"**Error:** {exc}"


def _require_account(account_id: str | None) -> str:
    if account_id is None or not str(account_id).strip():
        raise ValidationError("Please select an account.")
    return str(account_id).strip()


def _refresh_account_dropdown(selected: str | None = None):
    service = get_global_service()
    accounts = service.list_accounts()
    choices = accounts_to_dropdown_choices(accounts)
    kwargs: dict[str, Any] = {"choices": choices}
    if selected is not None:
        kwargs["value"] = selected if any(v == selected for _, v in choices) else None
    else:
        kwargs["value"] = choices[-1][1] if choices else None
    return gr.update(**kwargs)


def handle_create_account(owner_name: str, initial_deposit) -> tuple[str, object]:
    try:
        deposit = decimal_from_user_number(initial_deposit, "Initial deposit")
        account = get_global_service().create_account(owner_name, deposit)
        status = (
            f"**Success:** Created account `{account.account_id}` for **{account.owner_name}** "
            f"with initial deposit {format_decimal_money(deposit)}."
        )
        return status, _refresh_account_dropdown(account.account_id)
    except (TradingAppError, Exception) as exc:
        msg = exc if isinstance(exc, TradingAppError) else ValidationError(str(exc))
        return _safe_error_message(msg), _refresh_account_dropdown(None)


def handle_refresh_accounts() -> tuple[object, str]:
    return _refresh_account_dropdown(None), "**Accounts refreshed.**"


def handle_deposit(account_id: str | None, amount) -> str:
    try:
        aid = _require_account(account_id)
        amt = decimal_from_user_number(amount, "Amount")
        tx = get_global_service().deposit(aid, amt)
        return f"**Success:** Deposited {format_decimal_money(amt)} into `{aid}` (transaction `{tx.transaction_id}`)."
    except (TradingAppError, Exception) as exc:
        msg = exc if isinstance(exc, TradingAppError) else ValidationError(str(exc))
        return _safe_error_message(msg)


def handle_withdraw(account_id: str | None, amount) -> str:
    try:
        aid = _require_account(account_id)
        amt = decimal_from_user_number(amount, "Amount")
        tx = get_global_service().withdraw(aid, amt)
        return f"**Success:** Withdrew {format_decimal_money(amt)} from `{aid}` (transaction `{tx.transaction_id}`)."
    except (TradingAppError, Exception) as exc:
        msg = exc if isinstance(exc, TradingAppError) else ValidationError(str(exc))
        return _safe_error_message(msg)


def handle_buy(account_id: str | None, symbol: str | None, quantity) -> str:
    try:
        aid = _require_account(account_id)
        if not symbol:
            raise ValidationError("Symbol is required.")
        qty = decimal_from_user_number(quantity, "Quantity")
        tx = get_global_service().buy_shares(aid, symbol, qty)
        return (
            f"**Success:** Bought {format_decimal_quantity(qty)} {tx.symbol} shares at "
            f"{format_decimal_money(tx.execution_price)} (transaction `{tx.transaction_id}`)."
        )
    except (TradingAppError, Exception) as exc:
        msg = exc if isinstance(exc, TradingAppError) else ValidationError(str(exc))
        return _safe_error_message(msg)


def handle_sell(account_id: str | None, symbol: str | None, quantity) -> str:
    try:
        aid = _require_account(account_id)
        if not symbol:
            raise ValidationError("Symbol is required.")
        qty = decimal_from_user_number(quantity, "Quantity")
        tx = get_global_service().sell_shares(aid, symbol, qty)
        return (
            f"**Success:** Sold {format_decimal_quantity(qty)} {tx.symbol} shares at "
            f"{format_decimal_money(tx.execution_price)} (transaction `{tx.transaction_id}`)."
        )
    except (TradingAppError, Exception) as exc:
        msg = exc if isinstance(exc, TradingAppError) else ValidationError(str(exc))
        return _safe_error_message(msg)


def handle_show_holdings(account_id: str | None, as_of_text: str | None) -> tuple[str, list[list[str]]]:
    try:
        aid = _require_account(account_id)
        as_of = parse_optional_datetime(as_of_text)
        holdings = get_global_service().get_holdings(aid, as_of=as_of)
        return f"**Holdings for `{aid}`**", holdings_to_table(holdings)
    except (TradingAppError, Exception) as exc:
        msg = exc if isinstance(exc, TradingAppError) else ValidationError(str(exc))
        return _safe_error_message(msg), []


def handle_show_valuation(account_id: str | None, as_of_text: str | None) -> tuple[str, list[list[str]], str]:
    try:
        aid = _require_account(account_id)
        as_of = parse_optional_datetime(as_of_text)
        valuation = get_global_service().get_portfolio_valuation(aid, as_of=as_of)
        return (
            f"**Valuation for `{aid}`**",
            valuation_to_positions_table(valuation),
            valuation_to_summary_markdown(valuation),
        )
    except (TradingAppError, Exception) as exc:
        msg = exc if isinstance(exc, TradingAppError) else ValidationError(str(exc))
        return _safe_error_message(msg), [], ""


def handle_show_transactions(account_id: str | None, start_time_text: str | None, end_time_text: str | None) -> tuple[str, list[list[str]]]:
    try:
        aid = _require_account(account_id)
        start_time = parse_optional_datetime(start_time_text)
        end_time = parse_optional_datetime(end_time_text)
        txs = get_global_service().list_transactions(aid, start_time=start_time, end_time=end_time)
        return f"**Transactions for `{aid}`**", transactions_to_table(txs)
    except (TradingAppError, Exception) as exc:
        msg = exc if isinstance(exc, TradingAppError) else ValidationError(str(exc))
        return _safe_error_message(msg), []


def build_ui():
    with gr.Blocks(theme=gr.themes.Soft(primary_hue="amber", secondary_hue="blue")) as demo:
        gr.Markdown(
            "# Trading Simulation Account Manager\n\n"
            "Create accounts, manage cash, trade shares, and review point-in-time holdings and P&L."
        )
        with gr.Row():
            account_dropdown = gr.Dropdown(
                label="Account",
                choices=[],
                interactive=True,
                allow_custom_value=False,
            )
            refresh_accounts_button = gr.Button(value="Refresh Accounts")
            refresh_status = gr.Markdown(value="")
        with gr.Tab("Create Account"):
            owner_name_input = gr.Textbox(label="Owner Name", placeholder="Jane Trader")
            initial_deposit_input = gr.Number(label="Initial Deposit")
            create_account_button = gr.Button(value="Create Account")
            create_account_status = gr.Markdown(value="")
            create_account_button.click(
                fn=handle_create_account,
                inputs=[owner_name_input, initial_deposit_input],
                outputs=[create_account_status, account_dropdown],
                api_name="create_account",
            )
        with gr.Tab("Cash"):
            cash_amount_input = gr.Number(label="Amount")
            deposit_button = gr.Button(value="Deposit")
            withdraw_button = gr.Button(value="Withdraw")
            cash_status = gr.Markdown(value="")
            deposit_button.click(
                fn=handle_deposit,
                inputs=[account_dropdown, cash_amount_input],
                outputs=[cash_status],
                api_name="deposit",
            )
            withdraw_button.click(
                fn=handle_withdraw,
                inputs=[account_dropdown, cash_amount_input],
                outputs=[cash_status],
                api_name="withdraw",
            )
        with gr.Tab("Trade"):
            symbol_dropdown = gr.Dropdown(
                label="Symbol",
                choices=["AAPL", "TSLA", "GOOGL"],
                interactive=True,
                allow_custom_value=False,
            )
            trade_quantity_input = gr.Number(label="Quantity")
            buy_button = gr.Button(value="Buy")
            sell_button = gr.Button(value="Sell")
            trade_status = gr.Markdown(value="")
            buy_button.click(
                fn=handle_buy,
                inputs=[account_dropdown, symbol_dropdown, trade_quantity_input],
                outputs=[trade_status],
                api_name="buy",
            )
            sell_button.click(
                fn=handle_sell,
                inputs=[account_dropdown, symbol_dropdown, trade_quantity_input],
                outputs=[trade_status],
                api_name="sell",
            )
        with gr.Tab("Holdings"):
            holdings_as_of_input = gr.Textbox(
                label="As Of Timestamp",
                placeholder="Optional ISO timestamp, e.g. 2024-01-01T10:30:00+00:00",
            )
            show_holdings_button = gr.Button(value="Show Holdings")
            holdings_status = gr.Markdown(value="")
            holdings_table = gr.Dataframe(
                label="Holdings",
                headers=["Symbol", "Quantity"],
                datatype=["str", "str"],
                interactive=False,
            )
            show_holdings_button.click(
                fn=handle_show_holdings,
                inputs=[account_dropdown, holdings_as_of_input],
                outputs=[holdings_status, holdings_table],
                api_name="show_holdings",
            )
        with gr.Tab("Valuation / P&L"):
            valuation_as_of_input = gr.Textbox(
                label="As Of Timestamp",
                placeholder="Optional ISO timestamp, e.g. 2024-01-01T10:30:00+00:00",
            )
            show_valuation_button = gr.Button(value="Show Valuation / P&L")
            valuation_status = gr.Markdown(value="")
            positions_table = gr.Dataframe(
                label="Position Valuation",
                headers=["Symbol", "Quantity", "Price", "Market Value"],
                datatype=["str", "str", "str", "str"],
                interactive=False,
            )
            valuation_summary = gr.Markdown(value="")
            show_valuation_button.click(
                fn=handle_show_valuation,
                inputs=[account_dropdown, valuation_as_of_input],
                outputs=[valuation_status, positions_table, valuation_summary],
                api_name="show_valuation",
            )
        with gr.Tab("Transactions"):
            transactions_start_input = gr.Textbox(label="Start Time", placeholder="Optional ISO timestamp")
            transactions_end_input = gr.Textbox(label="End Time", placeholder="Optional ISO timestamp")
            show_transactions_button = gr.Button(value="Show Transactions")
            transactions_status = gr.Markdown(value="")
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
            show_transactions_button.click(
                fn=handle_show_transactions,
                inputs=[account_dropdown, transactions_start_input, transactions_end_input],
                outputs=[transactions_status, transactions_table],
                api_name="show_transactions",
            )
        refresh_accounts_button.click(
            fn=handle_refresh_accounts,
            inputs=[],
            outputs=[account_dropdown, refresh_status],
            api_name="refresh_accounts",
        )
    return demo


demo = build_ui()

if __name__ == "__main__":
    demo.launch()
