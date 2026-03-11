from __future__ import annotations

from datetime import date, datetime, time
from decimal import Decimal
from decimal import InvalidOperation
from typing import Any

from django.utils import timezone


def coerce_text(value: object) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value.strip()
    if isinstance(value, (int, float, bool, Decimal)):
        return str(value)
    return str(value).strip()


def coerce_decimal(value: object) -> Decimal | None:
    if value is None:
        return None
    if isinstance(value, Decimal):
        return value
    if isinstance(value, bool):
        raise TypeError(f"숫자 변환 실패: {value!r}")
    if isinstance(value, (int, float)):
        return Decimal(str(value))

    text = str(value).strip().replace(",", "").replace("%", "")
    if not text:
        return None
    if text in {"-", "--", "null", "NULL", "none", "None"}:
        return None

    try:
        return Decimal(text)
    except (ArithmeticError, ValueError, TypeError, InvalidOperation) as exc:
        raise TypeError(f"숫자 변환 실패: {value!r}") from exc


def coerce_int(value: object) -> int | None:
    if value is None:
        return None
    if isinstance(value, bool):
        raise TypeError(f"정수 변환 실패: {value!r}")
    if isinstance(value, int):
        return value
    if isinstance(value, Decimal):
        if value == value.to_integral_value():
            return int(value)
        raise TypeError(f"정수 변환 실패: {value!r}")
    if isinstance(value, float):
        if value.is_integer():
            return int(value)
        raise TypeError(f"정수 변환 실패: {value!r}")

    text = str(value).strip().replace(",", "").replace("%", "")
    if not text:
        return None
    if text in {"-", "--", "null", "NULL", "none", "None"}:
        return None

    try:
        decimal_value = Decimal(text)
    except (ArithmeticError, ValueError, TypeError, InvalidOperation) as exc:
        raise TypeError(f"정수 변환 실패: {value!r}") from exc

    if decimal_value != decimal_value.to_integral_value():
        raise TypeError(f"정수 변환 실패: {value!r}")
    return int(decimal_value)


def coerce_date(value: object) -> date | None:
    if value is None:
        return None
    if isinstance(value, date) and not isinstance(value, datetime):
        return value
    if isinstance(value, datetime):
        return value.date()

    if isinstance(value, (int, float)):
        value = str(int(value))

    text = str(value).strip()
    if not text:
        return None
    if text in {"-", "--", "null", "NULL", "none", "None"}:
        return None

    for fmt in (
        "%Y%m%d",
        "%Y-%m-%d",
        "%Y.%m.%d",
        "%Y/%m/%d",
    ):
        try:
            return datetime.strptime(text, fmt).date()
        except ValueError:
            continue
    raise TypeError(f"날짜 변환 실패: {value!r}")


def coerce_datetime(value: object) -> datetime | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        if timezone.is_naive(value):
            return timezone.make_aware(value)
        return value
    if isinstance(value, date):
        return timezone.make_aware(datetime.combine(value, time.min))
    if isinstance(value, (int, float)):
        value = str(int(value))

    text = str(value).strip()
    if not text:
        return None
    if text in {"-", "--", "null", "NULL", "none", "None"}:
        return None

    for fmt in (
        "%Y%m%d%H%M%S",
        "%Y%m%d%H%M",
        "%Y%m%d %H%M%S",
        "%Y%m%d %H%M",
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%d %H:%M",
        "%Y.%m.%d %H:%M:%S",
        "%Y.%m.%d %H:%M",
        "%Y/%m/%d %H:%M:%S",
        "%Y/%m/%d %H:%M",
        "%Y%m%d",
    ):
        try:
            parsed = datetime.strptime(text, fmt)
            break
        except ValueError:
            continue
    else:
        try:
            parsed = datetime.fromisoformat(text)
        except ValueError as exc:
            raise TypeError(f"날짜/시간 변환 실패: {value!r}") from exc

    if timezone.is_naive(parsed):
        return timezone.make_aware(parsed)
    return parsed


def extract_output(payload: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(payload, dict):
        raise TypeError("응답 payload는 dict여야 합니다")

    output = payload.get("output")
    if isinstance(payload.get("output1"), dict):
        output = payload.get("output1")
    if not isinstance(output, dict):
        raise KeyError("필수 응답 키가 누락되었습니다: output")
    return output

