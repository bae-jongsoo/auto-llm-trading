from datetime import datetime, timedelta
from decimal import Decimal
from unittest.mock import MagicMock, patch

import pytest
from django.utils import timezone

from apps.asset.models import Asset
from apps.trader.models import DecisionHistory, OrderHistory
from apps.trader.services import (
    build_buy_prompt,
    build_sell_prompt,
    execute_buy,
    execute_sell,
    record_decision_history,
    run_trading_cycle,
)
from apps.dart.models import DartDisclosure
from apps.market.models import MarketSnapshot
from apps.news.models import News
from apps.ws.services import save_trade_tick
from shared.stock_universe import TARGET_CORP_CODES, TARGET_STOCKS


# ──────────────────────────────────────
# Fixtures
# ──────────────────────────────────────

@pytest.fixture
def mock_llm():
    """LLM 호출을 mock한다. 외부 경계 mock 패턴."""
    with patch("shared.external.llm.subprocess.run") as mock_run, \
         patch("apps.trader.services.send_telegram"):
        yield mock_run


PROMPT_MARKET_FIELDS = [
    "per",
    "pbr",
    "eps",
    "hts_avls",
    "hts_frgn_ehrt",
    "frgn_ntby_qty",
    "pgtr_ntby_qty",
    "vol_tnrt",
    "w52_hgpr",
    "w52_lwpr",
    "w52_hgpr_vrss_prpr_ctrt",
    "w52_lwpr_vrss_prpr_ctrt",
    "mrkt_warn_cls_code",
    "invt_caful_yn",
    "short_over_yn",
]


# ──────────────────────────────────────
# Helpers
# ──────────────────────────────────────

def _현금_생성(amount: Decimal = Decimal("1000000.00")) -> Asset:
    return Asset.objects.create(
        stock_code=None,
        quantity=1,
        unit_price=amount,
        total_amount=amount,
    )


def _보유종목_생성(
    stock_code: str = "005930",
    quantity: int = 3,
    unit_price: Decimal = Decimal("70000.00"),
) -> Asset:
    return Asset.objects.create(
        stock_code=stock_code,
        quantity=quantity,
        unit_price=unit_price,
        total_amount=unit_price * quantity,
    )


def _시장정보_생성(
    stock_code: str,
    *,
    published_at: datetime | None = None,
) -> MarketSnapshot:
    published_at = published_at or timezone.now().replace(microsecond=0)
    return MarketSnapshot.objects.create(
        stock_code=stock_code,
        external_id=MarketSnapshot.build_external_id(stock_code, published_at.isoformat()),
        published_at=published_at,
        per=Decimal("10.1200"),
        pbr=Decimal("1.3300"),
        eps=Decimal("8500.1000"),
        hts_avls=430123000000,
        hts_frgn_ehrt=Decimal("51.3200"),
        frgn_ntby_qty=124000,
        pgtr_ntby_qty=-35000,
        vol_tnrt=Decimal("0.8700"),
        w52_hgpr=88000,
        w52_lwpr=62000,
        w52_hgpr_vrss_prpr_ctrt=Decimal("-11.2500"),
        w52_lwpr_vrss_prpr_ctrt=Decimal("25.8100"),
        mrkt_warn_cls_code="00",
        invt_caful_yn="N",
        short_over_yn="N",
    )


def _뉴스_생성(
    stock_code: str,
    *,
    index: int,
    useful: bool | None,
    title: str | None = None,
    published_at: datetime | None = None,
) -> News:
    published_at = published_at or timezone.now().replace(microsecond=0)
    link = f"https://news.example.com/{stock_code}/{index}"
    return News.objects.create(
        stock_code=stock_code,
        external_id=News.build_external_id(stock_code, link),
        published_at=published_at,
        link=link,
        title=title or f"뉴스-{stock_code}-{index}",
        summary=f"요약-{stock_code}-{index}",
        useful=useful,
        description=f"설명-{stock_code}-{index}",
    )


def _공시_생성(
    stock_code: str,
    *,
    index: int,
    published_at: datetime | None = None,
) -> DartDisclosure:
    published_at = published_at or timezone.now().replace(microsecond=0)
    corp_code = TARGET_CORP_CODES[stock_code]
    rcept_no = f"20260311{index:08d}"
    return DartDisclosure.objects.create(
        stock_code=stock_code,
        corp_code=corp_code,
        rcept_no=rcept_no,
        external_id=DartDisclosure.build_external_id(corp_code, rcept_no),
        published_at=published_at,
        title=f"공시-{stock_code}-{index}",
        link=f"https://dart.example.com/{rcept_no}",
        description=f"공시요약-{stock_code}-{index}",
    )


def _체결틱_저장(stock_code: str, *, price: int = 70000, now: datetime | None = None) -> None:
    now = now or timezone.now().replace(microsecond=0)
    save_trade_tick(
        stock_code,
        {
            "trade_id": f"{stock_code}-{int(now.timestamp())}",
            "trade_time": "09:00:00",
            "price": price,
            "volume": 3,
        },
        now=now,
    )


def _매수_컨텍스트_생성(now: datetime) -> None:
    _현금_생성(Decimal("1000000.00"))
    for index, stock_code in enumerate(TARGET_STOCKS.keys(), start=1):
        _시장정보_생성(stock_code, published_at=now - timedelta(minutes=index))
        _공시_생성(stock_code, index=index, published_at=now - timedelta(days=1))
        _뉴스_생성(
            stock_code,
            index=index * 10,
            useful=True,
            published_at=now - timedelta(hours=1),
        )
        _뉴스_생성(
            stock_code,
            index=index * 10 + 1,
            useful=None,
            published_at=now - timedelta(hours=2),
        )
        _체결틱_저장(stock_code, price=70000 + index, now=now - timedelta(minutes=1))


def _매도_컨텍스트_생성(now: datetime, stock_code: str = "005930") -> None:
    _현금_생성(Decimal("790000.00"))
    _보유종목_생성(stock_code=stock_code, quantity=3, unit_price=Decimal("70000.00"))
    _시장정보_생성(stock_code, published_at=now - timedelta(minutes=1))
    _공시_생성(stock_code, index=1, published_at=now - timedelta(days=1))
    _뉴스_생성(stock_code, index=1, useful=True, published_at=now - timedelta(hours=1))
    _체결틱_저장(stock_code, price=71000, now=now - timedelta(minutes=1))


def _판단이력_생성(result: str = DecisionHistory.Result.HOLD) -> DecisionHistory:
    return DecisionHistory.objects.create(
        request_payload="prompt",
        response_payload="response",
        parsed_decision={"decision": {"result": result}},
        processing_time_ms=120,
        is_error=False,
        error_message=None,
        result=result,
    )


# ──────────────────────────────────────
# build_buy_prompt
# ──────────────────────────────────────

@pytest.mark.django_db
def test_매수프롬프트_생성_성공_대상10종목_정보_포함():
    now = timezone.now().replace(microsecond=0)
    _매수_컨텍스트_생성(now)

    prompt = build_buy_prompt(now=now)

    assert isinstance(prompt, str)
    assert prompt.strip() != ""
    for stock_code in TARGET_STOCKS:
        assert stock_code in prompt
    assert now.strftime("%Y-%m-%d") in prompt


@pytest.mark.django_db
def test_매수프롬프트_필수컨텍스트_시각자산시세시장공시뉴스수집시각_포함():
    now = timezone.now().replace(microsecond=0)
    _매수_컨텍스트_생성(now)

    prompt = build_buy_prompt(now=now)

    assert now.strftime("%Y-%m-%d") in prompt
    assert "1000000" in prompt
    assert "70001" in prompt
    assert "공시-005930-1" in prompt
    assert "뉴스-005930-10" in prompt
    assert "요약-005930-10" in prompt
    assert "collected_at" in prompt
    for field in PROMPT_MARKET_FIELDS:
        assert field in prompt


@pytest.mark.django_db
def test_매수프롬프트_뉴스필터_useful_true_or_null만_포함():
    now = timezone.now().replace(microsecond=0)
    _매수_컨텍스트_생성(now)
    _뉴스_생성(
        "005930",
        index=999,
        useful=False,
        title="제외되어야하는뉴스",
        published_at=now - timedelta(minutes=10),
    )

    prompt = build_buy_prompt(now=now)

    assert "뉴스-005930-10" in prompt
    assert "뉴스-005930-11" in prompt
    assert "제외되어야하는뉴스" not in prompt


@pytest.mark.django_db
def test_매수프롬프트_최근7일_공시만_포함():
    now = timezone.now().replace(microsecond=0)
    _매수_컨텍스트_생성(now)
    오래된_공시 = _공시_생성(
        "005930",
        index=999,
        published_at=now - timedelta(days=8),
    )

    prompt = build_buy_prompt(now=now)

    assert 오래된_공시.title not in prompt


@pytest.mark.django_db
def test_매수프롬프트_시장정보만_있어도_생성():
    now = timezone.now().replace(microsecond=0)
    _현금_생성(Decimal("1000000.00"))
    _시장정보_생성("005930", published_at=now)
    _체결틱_저장("005930", price=70000, now=now - timedelta(minutes=1))

    result = build_buy_prompt(now=now)
    assert result is not None
    assert "005930" in result


# ──────────────────────────────────────
# build_sell_prompt
# ──────────────────────────────────────

@pytest.mark.django_db
def test_매도프롬프트_생성_성공_보유1종목만_포함():
    now = timezone.now().replace(microsecond=0)
    _매도_컨텍스트_생성(now, stock_code="005930")
    _시장정보_생성("000660", published_at=now - timedelta(minutes=1))
    _공시_생성("000660", index=77, published_at=now - timedelta(days=1))
    _뉴스_생성("000660", index=77, useful=True, published_at=now - timedelta(hours=1))
    _체결틱_저장("000660", price=120000, now=now - timedelta(minutes=2))

    prompt = build_sell_prompt("005930", now=now)

    assert isinstance(prompt, str)
    assert prompt.strip() != ""
    assert "005930" in prompt
    assert "000660" not in prompt


@pytest.mark.django_db
def test_매도프롬프트_필수컨텍스트_시각자산시세시장공시뉴스수집시각_포함():
    now = timezone.now().replace(microsecond=0)
    _매도_컨텍스트_생성(now, stock_code="005930")

    prompt = build_sell_prompt("005930", now=now)

    assert now.strftime("%Y-%m-%d") in prompt
    assert "70000" in prompt  # 매수 단가
    assert "210000" in prompt  # 총 매수금액 (70000 * 3)
    assert "3주" in prompt  # 보유 수량
    assert "71000" in prompt  # 체결 틱 가격
    assert "공시-005930-1" in prompt
    assert "뉴스-005930-1" in prompt
    assert "collected_at" in prompt
    for field in PROMPT_MARKET_FIELDS:
        assert field in prompt


@pytest.mark.django_db
def test_매도프롬프트_뉴스는_최근10건만_포함():
    now = timezone.now().replace(microsecond=0)
    _매도_컨텍스트_생성(now, stock_code="005930")

    for index in range(12):
        _뉴스_생성(
            "005930",
            index=100 + index,
            useful=True,
            title=f"최신뉴스-{index}",
            published_at=now - timedelta(minutes=index),
        )

    prompt = build_sell_prompt("005930", now=now)

    assert "최신뉴스-0" in prompt
    assert "최신뉴스-9" in prompt
    assert "최신뉴스-10" not in prompt
    assert "최신뉴스-11" not in prompt


@pytest.mark.django_db
def test_매도프롬프트_뉴스필터_useful_true_or_null만_포함():
    now = timezone.now().replace(microsecond=0)
    _매도_컨텍스트_생성(now, stock_code="005930")
    _뉴스_생성(
        "005930",
        index=999,
        useful=False,
        title="매도프롬프트에서제외되어야하는뉴스",
        published_at=now - timedelta(minutes=10),
    )

    prompt = build_sell_prompt("005930", now=now)

    assert "뉴스-005930-1" in prompt
    assert "매도프롬프트에서제외되어야하는뉴스" not in prompt


@pytest.mark.django_db
def test_매도프롬프트_미보유_종목코드_실패():
    now = timezone.now().replace(microsecond=0)
    _매도_컨텍스트_생성(now, stock_code="005930")

    with pytest.raises(ValueError, match="보유|종목|미보유"):
        build_sell_prompt("000660", now=now)


@pytest.mark.django_db
def test_매도프롬프트_컨텍스트_일부누락_HOLD_반환():
    now = timezone.now().replace(microsecond=0)
    _현금_생성(Decimal("790000.00"))
    _보유종목_생성(stock_code="005930", quantity=3, unit_price=Decimal("70000.00"))

    result = build_sell_prompt("005930", now=now)
    assert result is None


# ──────────────────────────────────────
# record_decision_history
# ──────────────────────────────────────

@pytest.mark.django_db
def test_판단이력_저장_성공_BUY결과():
    saved = record_decision_history(
        request_payload="buy prompt",
        response_payload='{"decision":{"result":"BUY"}}',
        parsed_decision={"decision": {"result": "BUY", "stock_code": "005930", "price": 70000, "quantity": 1}},
        processing_time_ms=321,
        is_error=False,
        error_message=None,
    )

    assert saved.id is not None
    assert saved.result == DecisionHistory.Result.BUY
    assert saved.is_error is False
    assert saved.error_message is None


@pytest.mark.django_db
def test_판단이력_실패여부와_무관하게_항상저장():
    saved = record_decision_history(
        request_payload="prompt",
        response_payload="",
        parsed_decision={"decision": {"result": "HOLD"}},
        processing_time_ms=25,
        is_error=True,
        error_message="timeout",
    )

    assert DecisionHistory.objects.count() == 1
    assert saved.result == DecisionHistory.Result.HOLD
    assert saved.is_error is True
    assert "timeout" in (saved.error_message or "")


@pytest.mark.django_db
def test_판단이력_result_허용값아님_실패():
    with pytest.raises(ValueError, match="result|허용|BUY|SELL|HOLD"):
        record_decision_history(
            request_payload="prompt",
            response_payload='{"decision":{"result":"STRONG_BUY"}}',
            parsed_decision={"decision": {"result": "STRONG_BUY"}},
            processing_time_ms=30,
            is_error=False,
            error_message=None,
        )


# ──────────────────────────────────────
# execute_buy
# ──────────────────────────────────────

@pytest.mark.django_db
def test_매수주문_실행_성공_즉시체결로_주문결과동일():
    _현금_생성(Decimal("1000000.00"))
    decision_history = _판단이력_생성(DecisionHistory.Result.BUY)

    order = execute_buy(
        decision_history=decision_history,
        stock_code="005930",
        price=Decimal("70000.00"),
        quantity=2,
    )

    assert order.decision_history_id == decision_history.id
    assert order.stock_code == "005930"
    assert order.order_price == Decimal("70000.00")
    assert order.order_quantity == 2
    assert order.order_total_amount == Decimal("140000.00")
    assert order.result_price == order.order_price
    assert order.result_quantity == order.order_quantity
    assert order.result_total_amount == order.order_total_amount
    assert order.result_executed_at is not None

    cash = Asset.objects.get(stock_code__isnull=True)
    position = Asset.objects.get(stock_code="005930")
    assert cash.total_amount == Decimal("860000.00")
    assert cash.unit_price == cash.total_amount
    assert position.quantity == 2
    assert position.total_amount == Decimal("140000.00")


@pytest.mark.django_db
def test_매수주문_가격또는수량이_0이하이면_실패():
    _현금_생성(Decimal("1000000.00"))
    decision_history = _판단이력_생성(DecisionHistory.Result.BUY)

    with pytest.raises(ValueError, match="가격|수량|0|양수"):
        execute_buy(
            decision_history=decision_history,
            stock_code="005930",
            price=Decimal("0"),
            quantity=1,
        )


@pytest.mark.django_db
def test_매수주문_이미_보유종목이_있으면_실패():
    _현금_생성(Decimal("1000000.00"))
    _보유종목_생성(stock_code="005930", quantity=1, unit_price=Decimal("70000.00"))
    decision_history = _판단이력_생성(DecisionHistory.Result.BUY)

    with pytest.raises(ValueError, match="보유|매수|불가"):
        execute_buy(
            decision_history=decision_history,
            stock_code="005930",
            price=Decimal("71000.00"),
            quantity=1,
        )


@pytest.mark.django_db
def test_매수주문_판단결과가_BUY가_아니면_실패():
    _현금_생성(Decimal("1000000.00"))
    decision_history = _판단이력_생성(DecisionHistory.Result.HOLD)

    with pytest.raises(ValueError, match="BUY|판단|result"):
        execute_buy(
            decision_history=decision_history,
            stock_code="005930",
            price=Decimal("70000.00"),
            quantity=1,
        )


# ──────────────────────────────────────
# execute_sell
# ──────────────────────────────────────

@pytest.mark.django_db
def test_매도주문_실행_성공_즉시체결로_주문결과동일():
    _현금_생성(Decimal("790000.00"))
    _보유종목_생성(stock_code="005930", quantity=3, unit_price=Decimal("70000.00"))
    decision_history = _판단이력_생성(DecisionHistory.Result.SELL)

    order = execute_sell(
        decision_history=decision_history,
        stock_code="005930",
        price=Decimal("71000.00"),
        quantity=1,
    )

    assert order.decision_history_id == decision_history.id
    assert order.stock_code == "005930"
    assert order.order_price == Decimal("71000.00")
    assert order.order_quantity == 1
    assert order.order_total_amount == Decimal("71000.00")
    assert order.result_price == order.order_price
    assert order.result_quantity == order.order_quantity
    assert order.result_total_amount == order.order_total_amount
    assert order.result_executed_at is not None

    cash = Asset.objects.get(stock_code__isnull=True)
    position = Asset.objects.get(stock_code="005930")
    assert cash.total_amount == Decimal("861000.00")
    assert cash.unit_price == cash.total_amount
    assert position.quantity == 2
    assert position.total_amount == Decimal("140000.00")


@pytest.mark.django_db
def test_매도주문_미보유상태에서_SELL_시도_실패():
    _현금_생성(Decimal("1000000.00"))
    decision_history = _판단이력_생성(DecisionHistory.Result.SELL)

    with pytest.raises(ValueError, match="미보유|보유하고 있지"):
        execute_sell(
            decision_history=decision_history,
            stock_code="005930",
            price=Decimal("71000.00"),
            quantity=1,
        )


@pytest.mark.django_db
def test_매도주문_보유수량_초과_실패():
    _현금_생성(Decimal("790000.00"))
    _보유종목_생성(stock_code="005930", quantity=2, unit_price=Decimal("70000.00"))
    decision_history = _판단이력_생성(DecisionHistory.Result.SELL)

    with pytest.raises(ValueError, match="수량|초과"):
        execute_sell(
            decision_history=decision_history,
            stock_code="005930",
            price=Decimal("71000.00"),
            quantity=3,
        )


@pytest.mark.django_db
def test_매도주문_판단결과가_SELL이_아니면_실패():
    _현금_생성(Decimal("790000.00"))
    _보유종목_생성(stock_code="005930", quantity=1, unit_price=Decimal("70000.00"))
    decision_history = _판단이력_생성(DecisionHistory.Result.HOLD)

    with pytest.raises(ValueError, match="SELL|판단|result"):
        execute_sell(
            decision_history=decision_history,
            stock_code="005930",
            price=Decimal("71000.00"),
            quantity=1,
        )


# ──────────────────────────────────────
# run_trading_cycle
# ──────────────────────────────────────

@pytest.mark.django_db
def test_트레이딩사이클_미보유시_매수판단_및_주문실행(mock_llm):
    now = timezone.now().replace(microsecond=0)
    _매수_컨텍스트_생성(now)
    mock_llm.return_value = MagicMock(
        returncode=0,
        stdout='{"decision":{"result":"BUY","stock_code":"005930","price":70000,"quantity":1}}',
        stderr="",
    )

    decision = run_trading_cycle(now=now)

    assert decision.result == DecisionHistory.Result.BUY
    assert decision.is_error is False
    assert DecisionHistory.objects.count() == 1
    assert OrderHistory.objects.count() == 1
    order = OrderHistory.objects.get()
    assert order.stock_code == "005930"


@pytest.mark.django_db
def test_트레이딩사이클_보유시_매도판단_및_주문실행(mock_llm):
    now = timezone.now().replace(microsecond=0)
    _매도_컨텍스트_생성(now, stock_code="005930")
    mock_llm.return_value = MagicMock(
        returncode=0,
        stdout='{"decision":{"result":"SELL","stock_code":"005930","price":71000,"quantity":1}}',
        stderr="",
    )

    decision = run_trading_cycle(now=now)

    assert decision.result == DecisionHistory.Result.SELL
    assert decision.is_error is False
    assert DecisionHistory.objects.count() == 1
    assert OrderHistory.objects.count() == 1
    assert OrderHistory.objects.get().stock_code == "005930"


@pytest.mark.django_db
def test_트레이딩사이클_HOLD면_주문이력_생성안함(mock_llm):
    now = timezone.now().replace(microsecond=0)
    _매수_컨텍스트_생성(now)
    mock_llm.return_value = MagicMock(
        returncode=0,
        stdout='{"decision":{"result":"HOLD"}}',
        stderr="",
    )

    decision = run_trading_cycle(now=now)

    assert decision.result == DecisionHistory.Result.HOLD
    assert DecisionHistory.objects.count() == 1
    assert OrderHistory.objects.count() == 0


@pytest.mark.django_db
def test_트레이딩사이클_LLM_타임아웃시_HOLD_에러이력저장(mock_llm):
    now = timezone.now().replace(microsecond=0)
    _매수_컨텍스트_생성(now)
    mock_llm.side_effect = TimeoutError("timeout")

    decision = run_trading_cycle(now=now)

    assert decision.result == DecisionHistory.Result.HOLD
    assert decision.is_error is True
    assert DecisionHistory.objects.count() == 1
    assert OrderHistory.objects.count() == 0


@pytest.mark.django_db
def test_트레이딩사이클_LLM_응답파싱실패시_HOLD_에러이력저장(mock_llm):
    now = timezone.now().replace(microsecond=0)
    _매수_컨텍스트_생성(now)
    mock_llm.return_value = MagicMock(
        returncode=0,
        stdout="not-json",
        stderr="",
    )

    decision = run_trading_cycle(now=now)

    assert decision.result == DecisionHistory.Result.HOLD
    assert decision.is_error is True
    assert DecisionHistory.objects.count() == 1
    assert OrderHistory.objects.count() == 0


@pytest.mark.django_db
def test_트레이딩사이클_LLM_빈응답시_HOLD_에러이력저장(mock_llm):
    now = timezone.now().replace(microsecond=0)
    _매수_컨텍스트_생성(now)
    mock_llm.return_value = MagicMock(
        returncode=0,
        stdout="   ",
        stderr="",
    )

    decision = run_trading_cycle(now=now)

    assert decision.result == DecisionHistory.Result.HOLD
    assert decision.is_error is True
    assert DecisionHistory.objects.count() == 1
    assert OrderHistory.objects.count() == 0


@pytest.mark.django_db
def test_트레이딩사이클_BUY응답_필수값누락이면_HOLD_주문미실행(mock_llm):
    now = timezone.now().replace(microsecond=0)
    _매수_컨텍스트_생성(now)
    mock_llm.return_value = MagicMock(
        returncode=0,
        stdout='{"decision":{"result":"BUY","stock_code":"005930","price":70000}}',
        stderr="",
    )

    decision = run_trading_cycle(now=now)

    assert decision.result == DecisionHistory.Result.HOLD
    assert DecisionHistory.objects.count() == 1
    assert OrderHistory.objects.count() == 0


@pytest.mark.django_db
def test_트레이딩사이클_result_허용값아님이면_HOLD_에러이력저장(mock_llm):
    now = timezone.now().replace(microsecond=0)
    _매수_컨텍스트_생성(now)
    mock_llm.return_value = MagicMock(
        returncode=0,
        stdout='{"decision":{"result":"STRONG_BUY","stock_code":"005930","price":70000,"quantity":1}}',
        stderr="",
    )

    decision = run_trading_cycle(now=now)

    assert decision.result == DecisionHistory.Result.HOLD
    assert decision.is_error is True
    assert DecisionHistory.objects.count() == 1
    assert OrderHistory.objects.count() == 0
