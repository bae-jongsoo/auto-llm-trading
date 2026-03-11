from __future__ import annotations

import requests
from django.conf import settings

from shared.stock_universe import validate_stock_code

KIS_BASE_URL = "https://openapi.koreainvestment.com:9443"
KIS_TOKEN_URL = f"{KIS_BASE_URL}/oauth2/tokenP"
KIS_INQUIRE_PRICE_URL = (
    f"{KIS_BASE_URL}/uapi/domestic-stock/v1/quotations/inquire-price"
)
KIS_TR_ID_INQUIRE_PRICE = "FHKST01010100"


def fetch_inquire_price(stock_code: str) -> dict:
    normalized_stock_code = validate_stock_code(stock_code)
    access_token = _issue_access_token()

    try:
        response = requests.get(
            KIS_INQUIRE_PRICE_URL,
            headers={
                "authorization": f"Bearer {access_token}",
                "appkey": settings.KIS_APP_KEY,
                "appsecret": settings.KIS_APP_SECRET,
                "tr_id": KIS_TR_ID_INQUIRE_PRICE,
                "custtype": "P",
            },
            params={
                "fid_cond_mrkt_div_code": "J",
                "fid_input_iscd": normalized_stock_code,
            },
            timeout=8,
        )
        response.raise_for_status()
    except requests.RequestException as exc:
        raise RuntimeError(f"KIS 현재정보 조회 실패: {exc}") from exc

    try:
        payload = response.json()
    except ValueError as exc:
        raise RuntimeError("KIS 응답 JSON 파싱 실패") from exc

    if str(payload.get("rt_cd")) != "0":
        error_message = payload.get("msg1") or payload.get("msg_cd") or "알 수 없는 오류"
        raise RuntimeError(f"KIS API 오류/실패: {error_message}")

    output = payload.get("output")
    if not isinstance(output, dict):
        raise RuntimeError("KIS API 비정상 응답: output 필드가 없습니다")

    return output


def _issue_access_token() -> str:
    _validate_required_settings()

    try:
        response = requests.post(
            KIS_TOKEN_URL,
            headers={"content-type": "application/json"},
            json={
                "grant_type": "client_credentials",
                "appkey": settings.KIS_APP_KEY,
                "appsecret": settings.KIS_APP_SECRET,
            },
            timeout=8,
        )
        response.raise_for_status()
    except requests.RequestException as exc:
        raise RuntimeError(f"KIS 인증 실패: {exc}") from exc

    try:
        payload = response.json()
    except ValueError as exc:
        raise RuntimeError("KIS 인증 응답 JSON 파싱 실패") from exc

    access_token = (payload.get("access_token") or "").strip()
    if not access_token:
        raise RuntimeError("KIS 인증 실패: access_token 누락")
    return access_token


def _validate_required_settings() -> None:
    missing_keys = [
        key
        for key, value in {
            "KIS_APP_KEY": settings.KIS_APP_KEY,
            "KIS_APP_SECRET": settings.KIS_APP_SECRET,
            "KIS_HTS_ID": settings.KIS_HTS_ID,
            "KIS_ACCT_STOCK": settings.KIS_ACCT_STOCK,
            "KIS_PROD_TYPE": settings.KIS_PROD_TYPE,
        }.items()
        if not value
    ]
    if missing_keys:
        raise RuntimeError(
            "KIS 설정값 누락: {}".format(", ".join(missing_keys))
        )
