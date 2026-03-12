from __future__ import annotations

from datetime import datetime

from django.db import transaction
from django.utils.dateparse import parse_datetime

from apps.dart.models import DartDisclosure
from shared.external.dart_api import fetch_disclosures
from shared.stock_universe import resolve_target_corp_codes


def upsert_disclosures(stock_code: str, corp_code: str, rows: list[dict]) -> list[DartDisclosure]:
    saved_disclosures: list[DartDisclosure] = []

    with transaction.atomic():
        for row in rows:
            rcept_no = (row.get("rcept_no") or "").strip()
            if not rcept_no:
                raise ValueError("rcept_no가 없어 external_id 생성 불가: rcept_no/external_id 필수")

            external_id = DartDisclosure.build_external_id(corp_code, rcept_no)
            disclosure, _ = DartDisclosure.objects.update_or_create(
                external_id=external_id,
                defaults={
                    "stock_code": stock_code,
                    "corp_code": corp_code,
                    "rcept_no": rcept_no,
                    "title": ((row.get("title") or row.get("report_nm") or "").strip()),
                    "link": (row.get("link") or "").strip(),
                    "description": _normalize_description(row.get("description")),
                    "published_at": _normalize_published_at(row.get("published_at")),
                },
            )
            saved_disclosures.append(disclosure)

    return saved_disclosures


def collect_dart(stock_codes: list[str] | None = None) -> dict:
    target_corp_codes = resolve_target_corp_codes(stock_codes)

    fetched_items_count = 0
    saved_items_count = 0

    for stock_code, corp_code in target_corp_codes.items():
        rows = fetch_disclosures(corp_code)
        fetched_items_count += len(rows)

        saved_rows = upsert_disclosures(stock_code=stock_code, corp_code=corp_code, rows=rows)
        saved_items_count += len(saved_rows)

    return {
        "stock_codes": list(target_corp_codes.keys()),
        "fetched_items": fetched_items_count,
        "saved_items": saved_items_count,
    }


def _normalize_description(raw_description: object) -> str | None:
    if raw_description is None:
        return None
    return str(raw_description).strip() or None


def _normalize_published_at(raw_published_at: object) -> datetime | None:
    if raw_published_at in (None, ""):
        return None
    if isinstance(raw_published_at, datetime):
        return raw_published_at
    if isinstance(raw_published_at, str):
        return parse_datetime(raw_published_at)
    return None
