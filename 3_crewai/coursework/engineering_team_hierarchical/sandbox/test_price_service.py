from __future__ import annotations

import unittest
from datetime import datetime, timezone
from decimal import Decimal

from exceptions import UnknownSymbolError
from price_service import PriceService, get_share_price


class PriceServiceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.service = PriceService()
        self.as_of = datetime(2024, 1, 1, 10, 30, tzinfo=timezone.utc)

    def test_get_share_price_supported_aapl(self) -> None:
        self.assertEqual(get_share_price("AAPL"), 150.0)

    def test_get_share_price_supported_tsla(self) -> None:
        self.assertEqual(get_share_price("TSLA"), 250.0)

    def test_get_share_price_supported_googl(self) -> None:
        self.assertEqual(get_share_price("GOOGL"), 2800.0)

    def test_get_price_normalizes_lowercase_symbol(self) -> None:
        self.assertEqual(self.service.get_price("aapl", self.as_of), Decimal("150"))

    def test_get_price_unknown_symbol_raises(self) -> None:
        with self.assertRaises(UnknownSymbolError):
            self.service.get_price("MSFT", self.as_of)

    def test_get_price_returns_decimal(self) -> None:
        price = self.service.get_price("TSLA", self.as_of)
        self.assertIsInstance(price, Decimal)
        self.assertEqual(price, Decimal("250"))
