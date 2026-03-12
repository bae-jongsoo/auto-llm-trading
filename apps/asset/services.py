from decimal import Decimal

from django.db import transaction

from apps.asset.models import Asset


def _validate_positive_order(price: Decimal, quantity: int) -> None:
    if price <= 0:
        raise ValueError("가격은 0보다 커야 합니다")
    if quantity <= 0:
        raise ValueError("수량은 0보다 커야 합니다")


def get_cash_asset() -> Asset:
    cash_assets = list(Asset.objects.filter(stock_code__isnull=True))
    if len(cash_assets) != 1:
        raise RuntimeError("현금 row는 정확히 1건이어야 합니다")

    cash = cash_assets[0]
    if cash.quantity != 1:
        raise RuntimeError("현금 row quantity는 1이어야 합니다")
    if cash.unit_price != cash.total_amount:
        raise RuntimeError("현금 row unit_price와 total_amount가 일치해야 합니다")
    return cash


def get_open_position() -> Asset | None:
    positions = list(Asset.objects.filter(stock_code__isnull=False))
    if len(positions) > 1:
        raise RuntimeError("보유 종목은 동시에 1건만 허용됩니다")
    if not positions:
        return None
    return positions[0]


def apply_virtual_buy(stock_code: str, price: Decimal, quantity: int) -> tuple[Asset, Asset]:
    _validate_positive_order(price=price, quantity=quantity)
    buy_amount = price * quantity

    with transaction.atomic():
        cash = get_cash_asset()
        position = get_open_position()

        if position is not None and position.stock_code != stock_code:
            raise ValueError("다른 종목을 이미 보유 중입니다")
        if cash.total_amount < buy_amount:
            raise ValueError("현금이 부족합니다")

        cash.total_amount -= buy_amount
        cash.unit_price = cash.total_amount
        cash.save(update_fields=["total_amount", "unit_price", "updated_at"])

        if position is None:
            position = Asset.objects.create(
                stock_code=stock_code,
                quantity=quantity,
                unit_price=price,
                total_amount=buy_amount,
            )
        else:
            position.quantity += quantity
            position.total_amount += buy_amount
            position.unit_price = position.total_amount / position.quantity
            position.save(
                update_fields=["quantity", "unit_price", "total_amount", "updated_at"]
            )

    return cash, position


def apply_virtual_sell(stock_code: str, price: Decimal, quantity: int) -> tuple[Asset, Asset]:
    _validate_positive_order(price=price, quantity=quantity)
    sell_amount = price * quantity

    with transaction.atomic():
        cash = get_cash_asset()
        position = get_open_position()

        if position is None or position.stock_code != stock_code:
            raise ValueError("해당 종목을 보유하고 있지 않습니다")
        if quantity > position.quantity:
            raise ValueError("보유 수량을 초과해 매도할 수 없습니다")

        cash.total_amount += sell_amount
        cash.unit_price = cash.total_amount
        cash.save(update_fields=["total_amount", "unit_price", "updated_at"])

        remaining_quantity = position.quantity - quantity
        if remaining_quantity == 0:
            position.delete()
            position.quantity = 0
            position.total_amount = Decimal("0")
        else:
            position.quantity = remaining_quantity
            position.total_amount = position.unit_price * remaining_quantity
            position.save(
                update_fields=["quantity", "total_amount", "updated_at"]
            )

    return cash, position
