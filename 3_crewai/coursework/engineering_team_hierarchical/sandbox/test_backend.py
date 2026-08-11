from __future__ import annotations

import unittest
from datetime import datetime, timedelta, timezone
from decimal import Decimal

from account_service import AccountService
from exceptions import (
    AccountNotFoundError,
    InsufficientFundsError,
    InsufficientHoldingsError,
    UnknownSymbolError,
    ValidationError,
)
from formatters import (
    accounts_to_dropdown_choices,
    decimal_from_user_number,
    format_datetime,
    format_decimal_money,
    format_decimal_quantity,
    holdings_to_table,
    parse_optional_datetime,
    transactions_to_table,
    valuation_to_positions_table,
    valuation_to_summary_markdown,
)
from models import (
    Account,
    Holding,
    PositionValuation,
    Transaction,
    TRANSACTION_TYPE_BUY,
    TRANSACTION_TYPE_DEPOSIT,
    TRANSACTION_TYPE_SELL,
    TRANSACTION_TYPE_WITHDRAWAL,
)
from price_service import PriceService, get_share_price
from repository import InMemoryAccountRepository


UTC = timezone.utc


class RepositoryTests(unittest.TestCase):
    def test_add_get_save_and_exists(self) -> None:
        repo = InMemoryAccountRepository()
        account = Account(
            account_id="acc-1",
            owner_name="Alice",
            created_at=datetime(2024, 1, 1, 10, 0, tzinfo=UTC),
            initial_deposit=Decimal("100"),
            next_sequence=1,
            transactions=[],
        )
        self.assertFalse(repo.account_exists("acc-1"))
        repo.add_account(account)
        self.assertTrue(repo.account_exists("acc-1"))
        self.assertIs(repo.get_account("acc-1"), account)
        account.owner_name = "Alicia"
        repo.save_account(account)
        self.assertEqual(repo.get_account("acc-1").owner_name, "Alicia")

    def test_list_accounts_returns_live_objects_in_insertion_order(self) -> None:
        repo = InMemoryAccountRepository()
        a1 = Account("a1", "A", datetime(2024, 1, 1, tzinfo=UTC), Decimal("0"), 1, [])
        a2 = Account("a2", "B", datetime(2024, 1, 2, tzinfo=UTC), Decimal("0"), 1, [])
        repo.add_account(a1)
        repo.add_account(a2)
        self.assertEqual([a.account_id for a in repo.list_accounts()], ["a1", "a2"])
        repo.list_accounts()[0].owner_name = "Changed"
        self.assertEqual(repo.get_account("a1").owner_name, "Changed")

    def test_missing_account_raises(self) -> None:
        repo = InMemoryAccountRepository()
        with self.assertRaises(AccountNotFoundError):
            repo.get_account("missing")
        with self.assertRaises(AccountNotFoundError):
            repo.save_account(Account("missing", "x", datetime.now(UTC), Decimal("0"), 1, []))


class PriceServiceTests(unittest.TestCase):
    def test_fixed_prices_are_supported_and_case_insensitive(self) -> None:
        self.assertEqual(get_share_price("AAPL"), 150.0)
        self.assertEqual(get_share_price("tsla"), 250.0)
        self.assertEqual(get_share_price("GoOgL"), 2800.0)

    def test_unknown_symbol_raises(self) -> None:
        with self.assertRaises(UnknownSymbolError):
            get_share_price("MSFT")

    def test_price_service_returns_decimal(self) -> None:
        service = PriceService()
        self.assertEqual(service.get_price("aapl", datetime(2024, 1, 1, tzinfo=UTC)), Decimal("150.0"))
        self.assertIsInstance(service.get_price("TSLA"), Decimal)


class FormattersTests(unittest.TestCase):
    def test_decimal_from_user_number_coerces_and_validates(self) -> None:
        self.assertEqual(decimal_from_user_number(1, "x"), Decimal("1"))
        self.assertEqual(decimal_from_user_number("1.25", "x"), Decimal("1.25"))
        self.assertEqual(decimal_from_user_number(Decimal("2.50"), "x"), Decimal("2.50"))
        with self.assertRaises(ValidationError):
            decimal_from_user_number(None, "x")
        with self.assertRaises(ValidationError):
            decimal_from_user_number("abc", "x")

    def test_parse_optional_datetime_normalizes_timezone(self) -> None:
        self.assertIsNone(parse_optional_datetime(None))
        self.assertIsNone(parse_optional_datetime("   "))
        naive = parse_optional_datetime("2024-01-01T10:00:00")
        aware = parse_optional_datetime("2024-01-01T10:00:00+02:00")
        self.assertEqual(naive, datetime(2024, 1, 1, 10, 0, tzinfo=UTC))
        self.assertEqual(aware, datetime(2024, 1, 1, 8, 0, tzinfo=UTC))
        with self.assertRaises(ValidationError):
            parse_optional_datetime("not-a-date")

    def test_formatters_for_money_quantity_datetime_and_tables(self) -> None:
        self.assertEqual(format_decimal_money(Decimal("12.3")), "$12.30")
        self.assertEqual(format_decimal_quantity(Decimal("12.3000")), "12.3")
        self.assertEqual(format_decimal_quantity(Decimal("10")), "10")
        self.assertEqual(format_datetime(None), "—")
        self.assertEqual(format_datetime(datetime(2024, 1, 1, 10, 0, tzinfo=UTC)), "2024-01-01T10:00:00Z")

        account = Account("a1", "Alice", datetime(2024, 1, 1, tzinfo=UTC), Decimal("0"), 1, [])
        self.assertEqual(accounts_to_dropdown_choices([account]), [("Alice — a1", "a1")])

        tx = Transaction(
            "tx1",
            "a1",
            1,
            TRANSACTION_TYPE_DEPOSIT,
            datetime(2024, 1, 1, 10, 0, tzinfo=UTC),
            Decimal("100"),
            None,
            None,
            None,
            "init",
        )
        self.assertEqual(
            transactions_to_table([tx])[0],
            ["1", "2024-01-01T10:00:00Z", "DEPOSIT", "", "", "", "$100.00", "tx1"],
        )

        self.assertEqual(holdings_to_table([Holding("AAPL", Decimal("1.5"))]), [["AAPL", "1.5"]])

        valuation = type("V", (), {
            "positions": [PositionValuation("AAPL", Decimal("1.5"), Decimal("150"), Decimal("225"))],
            "account_id": "a1",
            "cash_balance": Decimal("100"),
            "securities_value": Decimal("225"),
            "total_value": Decimal("325"),
            "net_external_contributions": Decimal("200"),
            "profit_loss": Decimal("125"),
        })()
        self.assertEqual(valuation_to_positions_table(valuation), [["AAPL", "1.5", "$150.00", "$225.00"]])
        summary = valuation_to_summary_markdown(valuation)
        self.assertIn("`a1`", summary)
        self.assertIn("$325.00", summary)


class AccountServiceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.repo = InMemoryAccountRepository()
        self.price_service = PriceService()
        self.service = AccountService(self.repo, self.price_service)
        self.t0 = datetime(2024, 1, 1, 9, 0, tzinfo=UTC)
        self.t1 = datetime(2024, 1, 1, 10, 0, tzinfo=UTC)
        self.t2 = datetime(2024, 1, 1, 11, 0, tzinfo=UTC)
        self.t3 = datetime(2024, 1, 1, 12, 0, tzinfo=UTC)

    def test_create_account_and_initial_deposit_transaction(self) -> None:
        account = self.service.create_account(" Alice ", Decimal("1000"), timestamp=self.t0)
        self.assertEqual(account.owner_name, "Alice")
        self.assertEqual(account.created_at, self.t0)
        self.assertEqual(account.initial_deposit, Decimal("1000"))
        self.assertEqual(account.next_sequence, 2)
        self.assertEqual(len(account.transactions), 1)
        tx = account.transactions[0]
        self.assertEqual(tx.sequence, 1)
        self.assertEqual(tx.transaction_type, TRANSACTION_TYPE_DEPOSIT)
        self.assertEqual(tx.cash_delta, Decimal("1000"))
        self.assertEqual(tx.notes, "Initial deposit")

    def test_create_account_with_zero_initial_deposit_has_no_transaction(self) -> None:
        account = self.service.create_account("Bob", Decimal("0"), timestamp=self.t0)
        self.assertEqual(account.transactions, [])
        self.assertEqual(account.next_sequence, 1)

    def test_create_account_validation(self) -> None:
        with self.assertRaises(ValidationError):
            self.service.create_account("", Decimal("1"), timestamp=self.t0)
        with self.assertRaises(ValidationError):
            self.service.create_account("x", Decimal("-1"), timestamp=self.t0)

    def _funded_account(self):
        return self.service.create_account("Alice", Decimal("1000"), timestamp=self.t0)

    def test_deposit_withdraw_and_cash_balance(self) -> None:
        account = self._funded_account()
        self.service.deposit(account.account_id, Decimal("250"), timestamp=self.t1, notes="bonus")
        self.service.withdraw(account.account_id, Decimal("125"), timestamp=self.t2, notes="bill")
        self.assertEqual(self.service.get_cash_balance(account.account_id), Decimal("1125"))
        txs = self.service.list_transactions(account.account_id)
        self.assertEqual([t.transaction_type for t in txs], [TRANSACTION_TYPE_DEPOSIT, TRANSACTION_TYPE_DEPOSIT, TRANSACTION_TYPE_WITHDRAWAL])

    def test_deposit_withdraw_validation_and_balance_errors(self) -> None:
        account = self._funded_account()
        with self.assertRaises(ValidationError):
            self.service.deposit(account.account_id, Decimal("0"))
        with self.assertRaises(ValidationError):
            self.service.withdraw(account.account_id, Decimal("0"))
        with self.assertRaises(InsufficientFundsError):
            self.service.withdraw(account.account_id, Decimal("2000"))

    def test_buy_sell_holdings_and_values(self) -> None:
        account = self._funded_account()
        buy = self.service.buy_shares(account.account_id, "aapl", Decimal("2"), timestamp=self.t1)
        self.assertEqual(buy.transaction_type, TRANSACTION_TYPE_BUY)
        self.assertEqual(buy.symbol, "AAPL")
        self.assertEqual(buy.quantity, Decimal("2"))
        self.assertEqual(buy.execution_price, Decimal("150.0"))
        self.assertEqual(self.service.get_cash_balance(account.account_id), Decimal("700.0"))
        holdings = self.service.get_holdings(account.account_id)
        self.assertEqual([(h.symbol, h.quantity) for h in holdings], [("AAPL", Decimal("2"))])

        sell = self.service.sell_shares(account.account_id, "AAPL", Decimal("1"), timestamp=self.t2)
        self.assertEqual(sell.transaction_type, TRANSACTION_TYPE_SELL)
        self.assertEqual(self.service.get_cash_balance(account.account_id), Decimal("850.0"))
        self.assertEqual([(h.symbol, h.quantity) for h in self.service.get_holdings(account.account_id)], [("AAPL", Decimal("1"))])

    def test_buy_sell_validation_and_symbol_errors(self) -> None:
        account = self._funded_account()
        with self.assertRaises(ValidationError):
            self.service.buy_shares(account.account_id, "", Decimal("1"))
        with self.assertRaises(ValidationError):
            self.service.buy_shares(account.account_id, "AAPL", Decimal("0"))
        with self.assertRaises(UnknownSymbolError):
            self.service.buy_shares(account.account_id, "MSFT", Decimal("1"))
        self.service.buy_shares(account.account_id, "AAPL", Decimal("1"))
        with self.assertRaises(InsufficientHoldingsError):
            self.service.sell_shares(account.account_id, "AAPL", Decimal("2"))
        with self.assertRaises(UnknownSymbolError):
            self.service.sell_shares(account.account_id, "MSFT", Decimal("1"))

    def test_point_in_time_cash_holdings_valuation_and_pl(self) -> None:
        account = self._funded_account()
        self.service.buy_shares(account.account_id, "AAPL", Decimal("2"), timestamp=self.t1)
        self.service.sell_shares(account.account_id, "AAPL", Decimal("1"), timestamp=self.t3)
        self.assertEqual(self.service.get_cash_balance(account.account_id, as_of=self.t0), Decimal("1000"))
        self.assertEqual(self.service.get_cash_balance(account.account_id, as_of=self.t1), Decimal("700.0"))
        self.assertEqual(self.service.get_cash_balance(account.account_id, as_of=self.t3), Decimal("850.0"))
        self.assertEqual(self.service.get_holdings(account.account_id, as_of=self.t1)[0].quantity, Decimal("2"))
        self.assertEqual(self.service.get_holdings(account.account_id, as_of=self.t3)[0].quantity, Decimal("1"))

        valuation = self.service.get_portfolio_valuation(account.account_id, as_of=self.t1)
        self.assertEqual(valuation.cash_balance, Decimal("700.0"))
        self.assertEqual(valuation.securities_value, Decimal("300.0"))
        self.assertEqual(valuation.total_value, Decimal("1000.0"))
        self.assertEqual(valuation.net_external_contributions, Decimal("1000"))
        self.assertEqual(valuation.profit_loss, Decimal("0.0"))

        valuation2 = self.service.get_portfolio_valuation(account.account_id, as_of=self.t3)
        self.assertEqual(valuation2.cash_balance, Decimal("850.0"))
        self.assertEqual(valuation2.securities_value, Decimal("150.0"))
        self.assertEqual(valuation2.total_value, Decimal("1000.0"))
        self.assertEqual(valuation2.profit_loss, Decimal("0.0"))

    def test_list_transactions_is_sorted_and_filters_boundaries(self) -> None:
        account = self._funded_account()
        self.service.deposit(account.account_id, Decimal("1"), timestamp=self.t1)
        self.service.buy_shares(account.account_id, "AAPL", Decimal("1"), timestamp=self.t2)
        txs = self.service.list_transactions(account.account_id)
        self.assertEqual([tx.sequence for tx in txs], [1, 2, 3])
        self.assertEqual([tx.sequence for tx in self.service.list_transactions(account.account_id, start_time=self.t1)], [2, 3])
        self.assertEqual([tx.sequence for tx in self.service.list_transactions(account.account_id, end_time=self.t1)], [1, 2])
        self.assertEqual([tx.sequence for tx in self.service.list_transactions(account.account_id, start_time=self.t1, end_time=self.t2)], [2, 3])

    def test_repository_isolated_failure_does_not_create_transaction(self) -> None:
        account = self._funded_account()
        before = len(self.service.list_transactions(account.account_id))
        with self.assertRaises(InsufficientFundsError):
            self.service.buy_shares(account.account_id, "GOOGL", Decimal("1"), timestamp=self.t1)
        self.assertEqual(len(self.service.list_transactions(account.account_id)), before)

    def test_timezone_normalization_accepts_naive_datetimes(self) -> None:
        account = self._funded_account()
        naive_ts = datetime(2024, 1, 1, 10, 0)
        tx = self.service.deposit(account.account_id, Decimal("1"), timestamp=naive_ts)
        self.assertEqual(tx.timestamp.tzinfo, UTC)
        self.assertEqual(tx.timestamp, naive_ts.replace(tzinfo=UTC))


if __name__ == "__main__":
    unittest.main()
