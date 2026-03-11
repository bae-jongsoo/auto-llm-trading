from __future__ import annotations

from shared.stock_universe import validate_stock_code

def build_ws_subscribe_messages(stock_code: str) -> list[dict]:
    normalized_stock_code = validate_stock_code(stock_code)
    return [
        {
            "header": {
                "tr_type": "1",
                "tr_id": "H0STCNT0",
            },
            "body": {
                "input": {
                    "tr_id": "H0STCNT0",
                    "tr_key": normalized_stock_code,
                }
            },
        },
        {
            "header": {
                "tr_type": "1",
                "tr_id": "H0STASP0",
            },
            "body": {
                "input": {
                    "tr_id": "H0STASP0",
                    "tr_key": normalized_stock_code,
                }
            },
        },
    ]
