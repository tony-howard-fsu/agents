from __future__ import annotations

import unittest
from datetime import datetime, timezone
from decimal import Decimal

from account_service import AccountService
from price_service import PriceService
from repository import InMemoryAccountRepository


class PointInTimeBase(unittest.TestCase):
    def setUp(self) -> None:
        self.repo = InMemoryAccountRepository()
        self.service = AccountService(self.repo, PriceService())
        self.t0 = datetime(2024, 1, 1, 9, 0, tzinfo=timezone.utc)
        self.t1 = datetime(2024, 1, 1, 10, 0, tzinfo=timezone.utc)
        self.t2 = datetime(2024, 1, 1, 11, 0, tzinfo=timezone.utc)
        self.t3 = datetime(2024, 1, 1, 12, 0, tzinfo=timezone.utc)
        self.t4 = datetime(2024, 1, 1, 13, 0, tzinfo=timezone.utc)
        self.account = self.service.create_account("Alice", Decimal("1000"), timestamp=self.t0)
        self.service.buy_shares(self.account.account_id, "AAPL", Decimal("2"), timestamp=self.t1)
        self.service.sell_shares(self.account.account_id, "AAPL", Decimal("1"), timestamp=self.t3)


class PointInTimeHoldingsTests(PointInTimeBase):
    def test_holdings_before_any_trades_are_empty(self) -> None:
        self.assertEqual(self.service.get_holdings(self.account.account_id, as_of=self.t0), [])

    def test_holdings_after_buy_include_symbol_quantity(self) -> None:
        holdings = self.service.get_holdings(self.account.account_id, as_of=self.t2)
        self.assertEqual(len(holdings), 1)
        self.assertEqual(holdings[0].symbol, "AAPL")
        self.assertEqual(holdings[0].quantity, Decimal("2"))

    def test_holdings_between_buy_and_sell_include_pre_sell_quantity(self) -> None:
        holdings = self.service.get_holdings(self.account.account_id, as_of=self.t2)
        self.assertEqual(holdings[0].quantity, Decimal("2"))

    def test_holdings_after_sell_include_remaining_quantity(self) -> None:
        holdings = self.service.get_holdings(self.account.account_id, as_of=self.t4)
        self.assertEqual(holdings[0].quantity, Decimal("1"))

    def test_holdings_after_full_sell_omit_zero_quantity_symbol(self) -> None:
        self.service.sell_shares(self.account.account_id, "AAPL", Decimal("1"), timestamp=self.t4)
        self.assertEqual(self.service.get_holdings(self.account.account_id, as_of=self.t4), [])

    def test_as_of_includes_transactions_at_exact_timestamp(self) -> None:
        holdings = self.service.get_holdings(self.account.account_id, as_of=self.t3)
        self.assertEqual(holdings[0].quantity, Decimal("1"))


class PointInTimeCashTests(PointInTimeBase):
    def test_cash_before_initial_deposit_is_zero(self) -> None:
        self.assertEqual(self.service.get_cash_balance(self.account.account_id, as_of=self.t0.replace(hour=8)), Decimal("0"))

    def test_cash_after_deposit(self) -> None:
        self.assertEqual(self.service.get_cash_balance(self.account.account_id, as_of=self.t0), Decimal("1000"))

    def test_cash_after_buy(self) -> None:
        self.assertEqual(self.service.get_cash_balance(self.account.account_id, as_of=self.t2), Decimal("700"))

    def test_cash_between_buy_and_sell(self) -> None:
        self.assertEqual(self.service.get_cash_balance(self.account.account_id, as_of=self.t2), Decimal("700"))

    def test_cash_after_sell(self) -> None:
        self.assertEqual(self.service.get_cash_balance(self.account.account_id, as_of=self.t4), Decimal("850"))


class PointInTimeValuationTests(PointInTimeBase):
    def test_portfolio_value_with_cash_only(self) -> None:
        account = self.service.create_account("Bob", Decimal("500"), timestamp=self.t0)
        valuation = self.service.get_portfolio_valuation(account.account_id, as_of=self.t0)
        self.assertEqual(valuation.cash_balance, Decimal("500"))
        self.assertEqual(valuation.securities_value, Decimal("0"))
        self.assertEqual(valuation.total_value, Decimal("500"))

    def test_portfolio_value_with_cash_and_holdings(self) -> None:
        valuation = self.service.get_portfolio_valuation(self.account.account_id, as_of=self.t2)
        self.assertEqual(valuation.cash_balance, Decimal("700"))
        self.assertEqual(valuation.securities_value, Decimal("300"))
        self.assertEqual(valuation.total_value, Decimal("1000"))

    def test_profit_loss_zero_immediately_after_deposit(self) -> None:
        account = self.service.create_account("Bob", Decimal("500"), timestamp=self.t0)
        self.assertEqual(self.service.get_profit_loss(account.account_id, as_of=self.t0), Decimal("0"))

    def test_profit_loss_uses_net_external_contributions(self) -> None:
        valuation = self.service.get_portfolio_valuation(self.account.account_id, as_of=self.t2)
        self.assertEqual(valuation.net_external_contributions, Decimal("1000"))
        self.assertEqual(valuation.profit_loss, Decimal("0"))

    def test_profit_loss_after_withdrawal_is_not_artificial_loss(self) -> None:
        account = self.service.create_account("Carol", Decimal("1000"), timestamp=self.t0)
        self.service.withdraw(account.account_id, Decimal("200"), timestamp=self.t1)
        valuation = self.service.get_portfolio_valuation(account.account_id, as_of=self.t1)
        self.assertEqual(valuation.cash_balance, Decimal("800"))
        self.assertEqual(valuation.net_external_contributions, Decimal("800"))
        self.assertEqual(valuation.profit_loss, Decimal("0"))

    def test_valuation_as_of_filters_later_transactions(self) -> None:
        valuation = self.service.get_portfolio_valuation(self.account.account_id, as_of=self.t2)
        self.assertEqual(valuation.cash_balance, Decimal("700"))
        self.assertEqual(len(valuation.positions), 1)
        self.assertEqual(valuation.positions[0].quantity, Decimal("2"))
