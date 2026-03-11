from decimal import Decimal

from apps.asset.models import Asset


def get_cash_asset() -> Asset:
    raise NotImplementedError


def get_open_position() -> Asset | None:
    raise NotImplementedError


def apply_virtual_buy(stock_code: str, price: Decimal, quantity: int) -> tuple[Asset, Asset]:
    raise NotImplementedError


def apply_virtual_sell(stock_code: str, price: Decimal, quantity: int) -> tuple[Asset, Asset]:
    raise NotImplementedError
