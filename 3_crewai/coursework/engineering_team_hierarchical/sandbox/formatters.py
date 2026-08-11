from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from typing import Any

try:
    from exceptions import ValidationError
except Exception:  # pragma: no cover
    class ValidationError(Exception):
        pass


def _to_decimal(value: int | float | str | Decimal | None, field_name: str) -> Decimal:
    if value is None:
        raise ValidationError(f"{field_name} is required.")
    try:
        if isinstance(value, Decimal):
            return value
        return Decimal(str(value).strip())
    except (InvalidOperation, ValueError, TypeError):
        raise ValidationError(f"{field_name} must be a valid number.")


def decimal_from_user_number(value: int | float | str | Decimal | None, field_name: str) -> Decimal:
    return _to_decimal(value, field_name)


def parse_optional_datetime(value: str | None) -> datetime | None:
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    try:
        dt = datetime.fromisoformat(text)
    except ValueError:
        raise ValidationError("Timestamp must be a valid ISO 8601 datetime.")
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def format_decimal_money(value: Decimal) -> str:
    return f"${value.quantize(Decimal('0.01')):,.2f}"


def format_decimal_quantity(value: Decimal) -> str:
    normalized = value.normalize()
    return format(normalized, 'f') if normalized == normalized.to_integral() else format(normalized, 'f').rstrip('0').rstrip('.')


def format_datetime(value: datetime | None) -> str:
    if value is None:
        return "—"
    return value.astimezone(timezone.utc).isoformat().replace('+00:00', 'Z')


def accounts_to_dropdown_choices(accounts: list[Any]) -> list[tuple[str, str]]:
    choices: list[tuple[str, str]] = []
    for account in accounts:
        choices.append((f"{account.owner_name} — {account.account_id}", account.account_id))
    return choices


def transactions_to_table(transactions: list[Any]) -> list[list[str]]:
    rows: list[list[str]] = []
    for tx in transactions:
        rows.append([
            str(tx.sequence),
            format_datetime(tx.timestamp),
            tx.transaction_type,
            tx.symbol or "",
            format_decimal_quantity(tx.quantity) if tx.quantity is not None else "",
            format_decimal_money(tx.execution_price) if tx.execution_price is not None else "",
            format_decimal_money(tx.cash_delta),
            tx.transaction_id,
        ])
    return rows


def holdings_to_table(holdings: list[Any]) -> list[list[str]]:
    return [[h.symbol, format_decimal_quantity(h.quantity)] for h in holdings]


def valuation_to_positions_table(valuation: Any) -> list[list[str]]:
    return [[p.symbol, format_decimal_quantity(p.quantity), format_decimal_money(p.price), format_decimal_money(p.market_value)] for p in valuation.positions]


def valuation_to_summary_markdown(valuation: Any) -> str:
    return (
        f"**Account:** `{valuation.account_id}`\n\n"
        f"- Cash Balance: {format_decimal_money(valuation.cash_balance)}\n"
        f"- Securities Value: {format_decimal_money(valuation.securities_value)}\n"
        f"- Total Portfolio Value: {format_decimal_money(valuation.total_value)}\n"
        f"- Net External Contributions: {format_decimal_money(valuation.net_external_contributions)}\n"
        f"- Profit / Loss: {format_decimal_money(valuation.profit_loss)}"
    )
