from __future__ import annotations

TARGET_STOCKS = {
    "005930": "삼성전자",
    "000660": "SK하이닉스",
    "105560": "KB금융",
    "055550": "신한지주",
    "035420": "네이버",
    "035720": "카카오",
    "000720": "현대건설",
    "005380": "현대차",
    "000270": "기아",
    "034020": "두산에너빌리티",
}

STOCK_NAMES = TARGET_STOCKS


def validate_stock_code(stock_code: str) -> str:
    normalized = stock_code.strip()
    if not normalized:
        raise ValueError("종목코드는 필수입니다")
    if normalized not in TARGET_STOCKS:
        raise ValueError(f"지원하지 않는 종목코드입니다: {normalized}")
    return normalized


def resolve_stock_codes(stock_codes: list[str] | None = None) -> list[str]:
    if not stock_codes:
        return list(TARGET_STOCKS.keys())
    return list(dict.fromkeys(validate_stock_code(c) for c in stock_codes))


def resolve_target_corp_codes(stock_codes: list[str] | None = None) -> dict[str, str]:
    raise NotImplementedError
