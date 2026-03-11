from __future__ import annotations

from django.conf import settings

try:
    from OpenDartReader import OpenDartReader
except ImportError:  # pragma: no cover - 테스트에서 patch로 대체 가능해야 함
    OpenDartReader = None


def fetch_disclosures(corp_code: str) -> list[dict]:
    api_key = getattr(settings, "DART_API_KEY", "")
    if not api_key:
        raise RuntimeError("DART_API_KEY 설정이 필요합니다")
    if OpenDartReader is None:
        raise RuntimeError("OpenDartReader 패키지가 설치되지 않았습니다")

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
