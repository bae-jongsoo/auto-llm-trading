from __future__ import annotations

from datetime import date, datetime, time
from decimal import Decimal, InvalidOperation

from django.db import transaction
from django.utils import timezone
from django.utils.dateparse import parse_date, parse_datetime

from apps.market.models import MarketSnapshot
from shared.external.kis_quote import fetch_inquire_price
from shared.stock_universe import resolve_stock_codes, validate_stock_code

DECIMAL_FIELDS = [
    "per",
    "pbr",
    "eps",
    "bps",
    "cpfn",
    "w52_hgpr_vrss_prpr_ctrt",
    "w52_lwpr_vrss_prpr_ctrt",
    "d250_hgpr_vrss_prpr_rate",
    "d250_lwpr_vrss_prpr_rate",
    "dryy_hgpr_vrss_prpr_rate",
    "dryy_lwpr_vrss_prpr_rate",
    "hts_frgn_ehrt",
    "vol_tnrt",
    "whol_loan_rmnd_rate",
    "marg_rate",
    "apprch_rate",
]

INTEGER_FIELDS = [
    "hts_avls",
    "stck_fcam",
    "w52_hgpr",
    "w52_lwpr",
    "d250_hgpr",
    "d250_lwpr",
    "stck_dryy_hgpr",
    "stck_dryy_lwpr",
    "frgn_hldn_qty",
    "frgn_ntby_qty",
    "pgtr_ntby_qty",
    "last_ssts_cntg_qty",
]

DATE_FIELDS = [
    "w52_hgpr_date",
    "w52_lwpr_date",
    "d250_hgpr_date",
    "d250_lwpr_date",
    "dryy_hgpr_date",
    "dryy_lwpr_date",
]

STRING_FIELDS = [
    "stac_month",
    "lstn_stcn",
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
]

MARKET_COLLECT_FIELDS = [
    *DECIMAL_FIELDS[:4],
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


def normalize_market_snapshot(stock_code: str, payload: dict) -> dict:
    normalized_stock_code = validate_stock_code(stock_code)
    published_at = _parse_published_at(payload.get("published_at"))

    normalized: dict = {
        "stock_code": normalized_stock_code,
        "published_at": published_at,
    }

    for field in DECIMAL_FIELDS:
        normalized[field] = _parse_decimal(payload.get(field), field)
    for field in INTEGER_FIELDS:
        normalized[field] = _parse_integer(payload.get(field), field)
    for field in DATE_FIELDS:
        normalized[field] = _parse_date(payload.get(field), field)
    for field in STRING_FIELDS:
        normalized[field] = _parse_string(payload.get(field))

    return normalized


def upsert_market_snapshot(snapshot_data: dict) -> MarketSnapshot:
    published_at = snapshot_data.get("published_at")
    if published_at in (None, ""):
        raise ValueError("external_id 생성에 필요한 시각값이 없습니다: published_at 필수")

    external_id = MarketSnapshot.build_external_id(
        snapshot_data["stock_code"],
        published_at,
    )
    defaults = {
        "stock_code": snapshot_data["stock_code"],
        "published_at": published_at,
    }
    for field in MARKET_COLLECT_FIELDS:
        defaults[field] = snapshot_data.get(field)

    with transaction.atomic():
        snapshot, _ = MarketSnapshot.objects.update_or_create(
            external_id=external_id,
            defaults=defaults,
        )
    return snapshot


def collect_market_snapshots(stock_codes: list[str] | None = None) -> dict:
    target_stock_codes = resolve_stock_codes(stock_codes)

    fetched_items_count = 0
    saved_items_count = 0

    for stock_code in target_stock_codes:
        normalized_stock_code = validate_stock_code(stock_code)
        payload = fetch_inquire_price(normalized_stock_code)
        fetched_items_count += 1

        snapshot_data = normalize_market_snapshot(normalized_stock_code, payload)
        upsert_market_snapshot(snapshot_data)
        saved_items_count += 1

    return {
        "stock_codes": target_stock_codes,
        "fetched_items": fetched_items_count,
        "saved_items": saved_items_count,
    }


def to_prompt_fields(snapshot: MarketSnapshot) -> dict:
    return {field: getattr(snapshot, field) for field in PROMPT_FIELDS}


def _parse_published_at(raw_value: object) -> datetime:
    if raw_value in (None, ""):
        raise ValueError("external_id 생성에 필요한 시각값이 없습니다: published_at 필수")

    raw_text = str(raw_value).strip()
    parsed = parse_datetime(raw_text)
    if parsed is None:
        parsed = _parse_compact_datetime(raw_text)
    if parsed is None:
        parsed_date = _parse_flexible_date(raw_text)
        if parsed_date is None:
            raise ValueError("숫자/날짜 파싱 변환 실패: published_at")
        parsed = datetime.combine(parsed_date, time.min)

    if timezone.is_naive(parsed):
        return timezone.make_aware(parsed, timezone.get_current_timezone())
    return parsed


def _parse_decimal(raw_value: object, field_name: str) -> Decimal | None:
    if raw_value in (None, ""):
        return None

    try:
        return Decimal(str(raw_value).strip().replace(",", ""))
    except (InvalidOperation, ValueError) as exc:
        raise ValueError(f"숫자/날짜 파싱 변환 실패: {field_name}") from exc


def _parse_integer(raw_value: object, field_name: str) -> int | None:
    if raw_value in (None, ""):
        return None

    try:
        numeric = Decimal(str(raw_value).strip().replace(",", ""))
    except (InvalidOperation, ValueError) as exc:
        raise ValueError(f"숫자/날짜 파싱 변환 실패: {field_name}") from exc

    if numeric != numeric.to_integral_value():
        raise ValueError(f"숫자/날짜 파싱 변환 실패: {field_name}")

    return int(numeric)


def _parse_date(raw_value: object, field_name: str) -> date | None:
    if raw_value in (None, ""):
        return None

    raw_text = str(raw_value).strip()
    parsed = _parse_flexible_date(raw_text)
    if parsed is not None:
        return parsed

    parsed_datetime = parse_datetime(raw_text)
    if parsed_datetime is not None:
        return parsed_datetime.date()

    parsed_datetime = _parse_compact_datetime(raw_text)
    if parsed_datetime is not None:
        return parsed_datetime.date()

    raise ValueError(f"숫자/날짜 파싱 변환 실패: {field_name}")


def _parse_string(raw_value: object) -> str:
    if raw_value is None:
        return ""
    return str(raw_value).strip()


def _parse_flexible_date(raw_text: str) -> date | None:
    parsed = parse_date(raw_text)
    if parsed is not None:
        return parsed
    if len(raw_text) == 8 and raw_text.isdigit():
        return parse_date(f"{raw_text[:4]}-{raw_text[4:6]}-{raw_text[6:8]}")
    return None


def _parse_compact_datetime(raw_text: str) -> datetime | None:
    if len(raw_text) == 14 and raw_text.isdigit():
        return parse_datetime(
            f"{raw_text[:4]}-{raw_text[4:6]}-{raw_text[6:8]}T"
            f"{raw_text[8:10]}:{raw_text[10:12]}:{raw_text[12:14]}"
        )
    return None
