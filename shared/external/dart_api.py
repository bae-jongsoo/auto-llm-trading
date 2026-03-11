from __future__ import annotations

from django.conf import settings

from OpenDartReader import OpenDartReader


def fetch_disclosures(corp_code: str) -> list[dict]:
    api_key = settings.DART_API_KEY
    if not api_key:
        raise RuntimeError("DART_API_KEY 설정이 필요합니다")

    try:
        reader = OpenDartReader(api_key)
        rows = reader.list(corp_code)
    except Exception as exc:
        raise RuntimeError(f"OpenDartReader 호출 실패: {exc}") from exc

    if rows is None:
        return []
    if hasattr(rows, "to_dict"):
        return rows.to_dict("records")
    if isinstance(rows, dict):
        return [rows]
    return list(rows)
