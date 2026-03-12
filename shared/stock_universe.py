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

TARGET_CORP_CODES = {
    "005930": "00126380",
    "000660": "00164779",
    "105560": "00688996",
    "055550": "00382199",
    "035420": "00266961",
    "035720": "00258801",
    "000720": "00164478",
    "005380": "00164742",
    "000270": "00106641",
    "034020": "00159616",
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
    return stock_codes or list(TARGET_STOCKS.keys())


def resolve_target_corp_codes(stock_codes: list[str] | None = None) -> dict[str, str]:
    target_codes = resolve_stock_codes(stock_codes)

    missing_codes = [code for code in target_codes if not TARGET_CORP_CODES.get(code)]
    if missing_codes:
        raise RuntimeError(
            "corp_code 매핑 누락: {}".format(", ".join(missing_codes))
        )

    return {stock_code: TARGET_CORP_CODES[stock_code] for stock_code in target_codes}
