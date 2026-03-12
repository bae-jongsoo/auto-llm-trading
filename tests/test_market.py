from datetime import date, datetime, timezone as dt_timezone
from decimal import Decimal
from unittest.mock import MagicMock, patch

import pytest
from django.test import override_settings
from django.utils import timezone

from apps.market.models import MarketSnapshot
from apps.market.services import (
    collect_market_snapshots,
    normalize_market_snapshot,
    to_prompt_fields,
    upsert_market_snapshot,
)
from shared.external.kis import KisClient
from shared.stock_universe import TARGET_STOCKS

MARKET_COLLECT_FIELDS = [
    "per",
    "pbr",
    "eps",
    "bps",
    "stac_month",
    "lstn_stcn",
    "hts_avls",
    "cpfn",
    "stck_fcam",
    "w52_hgpr",
    "w52_hgpr_date",
    "w52_hgpr_vrss_prpr_ctrt",
    "w52_lwpr",
    "w52_lwpr_date",
    "w52_lwpr_vrss_prpr_ctrt",
    "d250_hgpr",
    "d250_hgpr_date",
    "d250_hgpr_vrss_prpr_rate",
    "d250_lwpr",
    "d250_lwpr_date",
    "d250_lwpr_vrss_prpr_rate",
    "stck_dryy_hgpr",
    "dryy_hgpr_date",
    "dryy_hgpr_vrss_prpr_rate",
    "stck_dryy_lwpr",
    "dryy_lwpr_date",
    "dryy_lwpr_vrss_prpr_rate",
    "hts_frgn_ehrt",
    "frgn_hldn_qty",
    "frgn_ntby_qty",
    "pgtr_ntby_qty",
    "vol_tnrt",
    "whol_loan_rmnd_rate",
    "marg_rate",
    "crdt_able_yn",
    "ssts_yn",
    "iscd_stat_cls_code",
    "mrkt_warn_cls_code",
    "invt_caful_yn",
    "short_over_yn",
    "sltr_yn",
    "mang_issu_cls_code",
    "temp_stop_yn",
    "oprc_rang_cont_yn",
    "clpr_rang_cont_yn",
    "grmn_rate_cls_code",
    "new_hgpr_lwpr_cls_code",
    "rprs_mrkt_kor_name",
    "bstp_kor_isnm",
    "vi_cls_code",
    "ovtm_vi_cls_code",
    "last_ssts_cntg_qty",
    "apprch_rate",
]

PROMPT_FIELDS = [
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


def _현재정보_payload(
    *,
    published_at: object = "2026-03-11T00:10:00+00:00",
    per: str = "10.1200",
) -> dict:
    return {
        "published_at": published_at,
        "per": per,
        "pbr": "1.3300",
        "eps": "8500.1000",
        "bps": "64000.0000",
        "stac_month": "12",
        "lstn_stcn": "5969782550",
        "hts_avls": "430123000000",
        "cpfn": "100.0000",
        "stck_fcam": "100",
        "w52_hgpr": "88000",
        "w52_hgpr_date": "2026-02-03",
        "w52_hgpr_vrss_prpr_ctrt": "-11.2500",
        "w52_lwpr": "62000",
        "w52_lwpr_date": "2025-10-14",
        "w52_lwpr_vrss_prpr_ctrt": "25.8100",
        "d250_hgpr": "91000",
        "d250_hgpr_date": "2025-04-19",
        "d250_hgpr_vrss_prpr_rate": "-14.2200",
        "d250_lwpr": "58000",
        "d250_lwpr_date": "2025-06-20",
        "d250_lwpr_vrss_prpr_rate": "34.4800",
        "stck_dryy_hgpr": "90500",
        "dryy_hgpr_date": "2025-08-07",
        "dryy_hgpr_vrss_prpr_rate": "-13.8500",
        "stck_dryy_lwpr": "56000",
        "dryy_lwpr_date": "2025-09-11",
        "dryy_lwpr_vrss_prpr_rate": "39.2800",
        "hts_frgn_ehrt": "51.3200",
        "frgn_hldn_qty": "3100050000",
        "frgn_ntby_qty": "124000",
        "pgtr_ntby_qty": "-35000",
        "vol_tnrt": "0.8700",
        "whol_loan_rmnd_rate": "0.4200",
        "marg_rate": "20.0000",
        "crdt_able_yn": "Y",
        "ssts_yn": "N",
        "iscd_stat_cls_code": "00",
        "mrkt_warn_cls_code": "00",
        "invt_caful_yn": "N",
        "short_over_yn": "N",
        "sltr_yn": "N",
        "mang_issu_cls_code": "",
        "temp_stop_yn": "N",
        "oprc_rang_cont_yn": "N",
        "clpr_rang_cont_yn": "N",
        "grmn_rate_cls_code": "00",
        "new_hgpr_lwpr_cls_code": "0",
        "rprs_mrkt_kor_name": "KOSPI",
        "bstp_kor_isnm": "전기전자",
        "vi_cls_code": "0",
        "ovtm_vi_cls_code": "0",
        "last_ssts_cntg_qty": "0",
        "apprch_rate": "0.0000",
    }


def _http_응답(payload: dict) -> MagicMock:
    response = MagicMock()
    response.raise_for_status.return_value = None
    response.json.return_value = payload
    return response


# ──────────────────────────────────────
# fetch_inquire_price
# ──────────────────────────────────────

@override_settings(
    KIS_APP_KEY="kis-app-key",
    KIS_APP_SECRET="kis-app-secret",
    KIS_HTS_ID="kis-hts-id",
    KIS_ACCT_STOCK="12345678",
    KIS_PROD_TYPE="01",
)
def test_KIS_현재정보조회_성공():
    output = _현재정보_payload()

    with patch("shared.external.kis.PyKis"):
        with patch("shared.external.kis.requests.get") as mock_get:
            mock_get.return_value = _http_응답({"rt_cd": "0", "output": output})

            client = KisClient()
            result = client.fetch_inquire_price("005930")

    assert isinstance(result, dict)
    assert result == output


@override_settings(
    KIS_APP_KEY="kis-app-key",
    KIS_APP_SECRET="kis-app-secret",
    KIS_HTS_ID="kis-hts-id",
    KIS_ACCT_STOCK="12345678",
    KIS_PROD_TYPE="01",
)
def test_KIS_현재정보조회_API오류_실패():
    with patch("shared.external.kis.PyKis"):
        with patch("shared.external.kis.requests.get") as mock_get:
            mock_get.return_value = _http_응답(
                {
                    "rt_cd": "1",
                    "msg1": "인증 실패",
                }
            )

            with pytest.raises(RuntimeError, match="KIS|인증|오류|실패"):
                client = KisClient()
                client.fetch_inquire_price("005930")


# ──────────────────────────────────────
# normalize_market_snapshot
# ──────────────────────────────────────

def test_현재정보_normalize_성공_숫자날짜_문자열_타입변환():
    normalized = normalize_market_snapshot("005930", _현재정보_payload())

    assert normalized["stock_code"] == "005930"
    assert timezone.is_aware(normalized["published_at"])
    assert normalized["published_at"].isoformat().startswith("2026-03-11T00:10:00")
    assert normalized["per"] == Decimal("10.1200")
    assert normalized["w52_hgpr"] == 88000
    assert normalized["w52_hgpr_date"] == date(2026, 2, 3)


def test_현재정보_normalize_external_id용_시각값_누락_실패():
    payload = _현재정보_payload()
    payload.pop("published_at")

    with pytest.raises(ValueError, match="external_id|시각|published_at|필수"):
        normalize_market_snapshot("005930", payload)


def test_현재정보_normalize_숫자날짜_파싱실패():
    payload = _현재정보_payload()
    payload["per"] = "not-a-number"

    with pytest.raises(ValueError, match="숫자|날짜|파싱|변환"):
        normalize_market_snapshot("005930", payload)


# ──────────────────────────────────────
# upsert_market_snapshot
# ──────────────────────────────────────

@pytest.mark.django_db
def test_현재정보_upsert_성공_전체필드저장_및_external_id_생성():
    snapshot_data = normalize_market_snapshot(
        "005930",
        _현재정보_payload(
            published_at=datetime(2026, 3, 11, 0, 10, 0, tzinfo=dt_timezone.utc),
        ),
    )

    saved = upsert_market_snapshot(snapshot_data)

    assert saved.stock_code == "005930"
    assert saved.external_id == MarketSnapshot.build_external_id(saved.stock_code, saved.published_at)
    for field in MARKET_COLLECT_FIELDS:
        assert getattr(saved, field) == snapshot_data[field]


@pytest.mark.django_db
def test_현재정보_upsert_동일_external_id_멱등_유지():
    base_published_at = datetime(2026, 3, 11, 0, 10, 0, tzinfo=dt_timezone.utc)

    first = upsert_market_snapshot(
        normalize_market_snapshot(
            "005930",
            _현재정보_payload(published_at=base_published_at, per="10.1000"),
        )
    )
    second = upsert_market_snapshot(
        normalize_market_snapshot(
            "005930",
            _현재정보_payload(published_at=base_published_at, per="12.3400"),
        )
    )

    assert MarketSnapshot.objects.count() == 1
    saved = MarketSnapshot.objects.get()
    assert saved.id == first.id
    assert saved.id == second.id
    assert saved.per == Decimal("12.3400")


# ──────────────────────────────────────
# collect_market_snapshots
# ──────────────────────────────────────

@pytest.mark.django_db
def test_현재정보_수집_성공_stock_codes_미지정시_대상10종목_전체수집():
    def _side_effect(stock_code: str) -> dict:
        return _현재정보_payload(per=str(int(stock_code[-2:]) + 0.1234))

    with patch("shared.external.kis.PyKis"):
        with patch.object(KisClient, "fetch_inquire_price", side_effect=_side_effect) as mock_fetch:
            result = collect_market_snapshots()

    assert isinstance(result, dict)
    assert mock_fetch.call_count == len(TARGET_STOCKS)
    assert {one_call.args[0] for one_call in mock_fetch.call_args_list} == set(TARGET_STOCKS.keys())
    assert MarketSnapshot.objects.count() == len(TARGET_STOCKS)


# ──────────────────────────────────────
# to_prompt_fields
# ──────────────────────────────────────

@pytest.mark.django_db
def test_프롬프트용_15개필드_추출_성공():
    snapshot = upsert_market_snapshot(
        normalize_market_snapshot(
            "005930",
            _현재정보_payload(published_at=datetime(2026, 3, 11, 0, 10, 0, tzinfo=dt_timezone.utc)),
        )
    )

    fields = to_prompt_fields(snapshot)

    assert list(fields.keys()) == PROMPT_FIELDS
    assert len(fields) == 15
    for field in PROMPT_FIELDS:
        assert fields[field] == getattr(snapshot, field)
