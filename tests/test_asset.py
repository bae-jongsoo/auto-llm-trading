from decimal import Decimal

import pytest
from apps.asset.models import Asset
from apps.asset.services import (
    apply_virtual_buy,
    apply_virtual_sell,
    get_cash_asset,
    get_open_position,
)


def _현금_생성(amount: Decimal) -> Asset:
    return Asset.objects.create(
        stock_code=None,
        quantity=1,
        unit_price=amount,
        total_amount=amount,
    )


def _보유종목_생성(stock_code: str, quantity: int, unit_price: Decimal) -> Asset:
    return Asset.objects.create(
        stock_code=stock_code,
        quantity=quantity,
        unit_price=unit_price,
        total_amount=unit_price * quantity,
    )


# ──────────────────────────────────────
# get_cash_asset
# ──────────────────────────────────────

@pytest.mark.django_db
def test_현금_row_조회_성공():
    _현금_생성(Decimal("1000000.00"))

    cash = get_cash_asset()

    assert cash.stock_code is None
    assert cash.quantity == 1
    assert cash.unit_price == cash.total_amount


@pytest.mark.django_db
def test_현금_row가_없으면_실패():
    with pytest.raises(RuntimeError):
        get_cash_asset()


@pytest.mark.django_db
def test_현금_row가_중복이면_실패():
    _현금_생성(Decimal("1000000.00"))
    _현금_생성(Decimal("500000.00"))

    with pytest.raises(RuntimeError):
        get_cash_asset()


@pytest.mark.django_db
def test_현금_row_수량규칙_위반이면_실패():
    Asset.objects.create(
        stock_code=None,
        quantity=2,
        unit_price=Decimal("1000000.00"),
        total_amount=Decimal("1000000.00"),
    )

    with pytest.raises(RuntimeError):
        get_cash_asset()


@pytest.mark.django_db
def test_현금_row_단가총액불일치면_실패():
    Asset.objects.create(
        stock_code=None,
        quantity=1,
        unit_price=Decimal("999999.99"),
        total_amount=Decimal("1000000.00"),
    )

    with pytest.raises(RuntimeError):
        get_cash_asset()


# ──────────────────────────────────────
# get_open_position
# ──────────────────────────────────────

@pytest.mark.django_db
def test_보유종목이_없으면_None_반환():
    _현금_생성(Decimal("1000000.00"))

    assert get_open_position() is None


@pytest.mark.django_db
def test_보유종목_1건_조회_성공():
    _현금_생성(Decimal("1000000.00"))
    _보유종목_생성("005930", quantity=3, unit_price=Decimal("70000.00"))

    position = get_open_position()

    assert position is not None
    assert position.stock_code == "005930"
    assert position.quantity == 3


@pytest.mark.django_db
def test_보유종목이_2건_이상이면_실패():
    _현금_생성(Decimal("1000000.00"))
    _보유종목_생성("005930", quantity=1, unit_price=Decimal("70000.00"))
    _보유종목_생성("000660", quantity=1, unit_price=Decimal("120000.00"))

    with pytest.raises(RuntimeError):
        get_open_position()


# ──────────────────────────────────────
# apply_virtual_buy
# ──────────────────────────────────────

@pytest.mark.django_db
def test_가상매수_성공_현금차감_및_보유생성():
    _현금_생성(Decimal("1000000.00"))

    cash, position = apply_virtual_buy("005930", Decimal("70000.00"), 3)

    assert cash.stock_code is None
    assert cash.quantity == 1
    assert cash.total_amount == Decimal("790000.00")
    assert cash.unit_price == cash.total_amount
    assert position.stock_code == "005930"
    assert position.quantity == 3
    assert position.total_amount == Decimal("210000.00")


@pytest.mark.django_db
def test_가상매수_동일종목_추가매수_성공():
    _현금_생성(Decimal("1000000.00"))
    _보유종목_생성("005930", quantity=2, unit_price=Decimal("70000.00"))

    cash, position = apply_virtual_buy("005930", Decimal("80000.00"), 2)

    assert cash.total_amount == Decimal("840000.00")
    assert cash.unit_price == cash.total_amount
    assert position.stock_code == "005930"
    assert position.quantity == 4
    assert position.total_amount == Decimal("300000.00")


@pytest.mark.django_db
def test_가상매수_가격이_0이하이면_실패():
    _현금_생성(Decimal("1000000.00"))

    with pytest.raises(ValueError):
        apply_virtual_buy("005930", Decimal("0"), 1)


@pytest.mark.django_db
def test_가상매수_수량이_0이하이면_실패():
    _현금_생성(Decimal("1000000.00"))

    with pytest.raises(ValueError):
        apply_virtual_buy("005930", Decimal("70000.00"), 0)


@pytest.mark.django_db
def test_가상매수_현금부족이면_실패():
    _현금_생성(Decimal("10000.00"))

    with pytest.raises(ValueError):
        apply_virtual_buy("005930", Decimal("70000.00"), 1)


@pytest.mark.django_db
def test_가상매수_이미_다른종목_보유중이면_실패():
    _현금_생성(Decimal("1000000.00"))
    _보유종목_생성("005930", quantity=1, unit_price=Decimal("70000.00"))

    with pytest.raises(ValueError):
        apply_virtual_buy("000660", Decimal("120000.00"), 1)


@pytest.mark.django_db
def test_가상매수_현금_row가_없으면_실패():
    with pytest.raises(RuntimeError):
        apply_virtual_buy("005930", Decimal("70000.00"), 1)


@pytest.mark.django_db
def test_가상매수_현금_row가_중복이면_실패():
    _현금_생성(Decimal("1000000.00"))
    _현금_생성(Decimal("500000.00"))

    with pytest.raises(RuntimeError):
        apply_virtual_buy("005930", Decimal("70000.00"), 1)


# ──────────────────────────────────────
# apply_virtual_sell
# ──────────────────────────────────────

@pytest.mark.django_db
def test_가상매도_성공_보유수량차감_및_현금증가():
    _현금_생성(Decimal("790000.00"))
    _보유종목_생성("005930", quantity=3, unit_price=Decimal("70000.00"))

    cash, position = apply_virtual_sell("005930", Decimal("71000.00"), 1)

    assert cash.stock_code is None
    assert cash.total_amount == Decimal("861000.00")
    assert cash.unit_price == cash.total_amount
    assert position.stock_code == "005930"
    assert position.quantity == 2


@pytest.mark.django_db
def test_가상매도_전량매도면_보유row_삭제():
    _현금_생성(Decimal("790000.00"))
    _보유종목_생성("005930", quantity=3, unit_price=Decimal("70000.00"))

    apply_virtual_sell("005930", Decimal("71000.00"), 3)

    assert Asset.objects.filter(stock_code="005930").count() == 0
    cash = Asset.objects.get(stock_code__isnull=True)
    assert cash.quantity == 1
    assert cash.unit_price == cash.total_amount


@pytest.mark.django_db
def test_가상매도_가격이_0이하이면_실패():
    _현금_생성(Decimal("1000000.00"))
    _보유종목_생성("005930", quantity=3, unit_price=Decimal("70000.00"))

    with pytest.raises(ValueError):
        apply_virtual_sell("005930", Decimal("-1"), 1)


@pytest.mark.django_db
def test_가상매도_수량이_0이하이면_실패():
    _현금_생성(Decimal("1000000.00"))
    _보유종목_생성("005930", quantity=3, unit_price=Decimal("70000.00"))

    with pytest.raises(ValueError):
        apply_virtual_sell("005930", Decimal("70000.00"), 0)


@pytest.mark.django_db
def test_가상매도_보유하지_않은_종목이면_실패():
    _현금_생성(Decimal("1000000.00"))

    with pytest.raises(ValueError):
        apply_virtual_sell("005930", Decimal("70000.00"), 1)


@pytest.mark.django_db
def test_가상매도_보유수량_초과면_실패():
    _현금_생성(Decimal("1000000.00"))
    _보유종목_생성("005930", quantity=2, unit_price=Decimal("70000.00"))

    with pytest.raises(ValueError):
        apply_virtual_sell("005930", Decimal("70000.00"), 3)


@pytest.mark.django_db
def test_가상매도_현금_row가_중복이면_실패():
    _현금_생성(Decimal("1000000.00"))
    _현금_생성(Decimal("500000.00"))
    _보유종목_생성("005930", quantity=1, unit_price=Decimal("70000.00"))

    with pytest.raises(RuntimeError):
        apply_virtual_sell("005930", Decimal("70000.00"), 1)


@pytest.mark.django_db
def test_가상매도_현금_row가_없으면_실패():
    _보유종목_생성("005930", quantity=1, unit_price=Decimal("70000.00"))

    with pytest.raises(RuntimeError):
        apply_virtual_sell("005930", Decimal("70000.00"), 1)


@pytest.mark.django_db
def test_가상체결은_수수료슬리피지없이_주문값_기준으로_반영():
    _현금_생성(Decimal("1000000.00"))

    apply_virtual_buy("005930", Decimal("70000.00"), 3)
    apply_virtual_sell("005930", Decimal("71000.00"), 3)

    cash = Asset.objects.get(stock_code__isnull=True)
    assert cash.total_amount == Decimal("1003000.00")
    assert cash.unit_price == cash.total_amount
    assert Asset.objects.filter(stock_code__isnull=False).count() == 0
