from __future__ import annotations

import os
import re
from html import unescape

import requests
from django.conf import settings

from shared.stock_universe import TARGET_STOCKS, validate_stock_code

NAVER_NEWS_API_URL = "https://openapi.naver.com/v1/search/news.json"


def fetch_news(stock_code: str, limit: int = 10) -> list[dict]:
    normalized_stock_code = validate_stock_code(stock_code)
    if limit <= 0:
        raise ValueError("limit은 1 이상이어야 합니다")

    client_id, client_secret = _get_naver_credentials()
    query = f"{TARGET_STOCKS[normalized_stock_code]} 주식"

    try:
        response = requests.get(
            NAVER_NEWS_API_URL,
            headers={
                "X-Naver-Client-Id": client_id,
                "X-Naver-Client-Secret": client_secret,
            },
            params={
                "query": query,
                "display": limit,
                "sort": "date",
            },
            timeout=8,
        )
        response.raise_for_status()
    except requests.RequestException as exc:
        raise RuntimeError(f"네이버 API 호출 실패: {exc}") from exc

    try:
        payload = response.json()
    except ValueError as exc:
        raise RuntimeError("네이버 API 응답 JSON 파싱 실패") from exc

    items = payload.get("items")
    if not isinstance(items, list):
        raise RuntimeError("네이버 API 비정상 응답: items 필드가 없습니다")

    normalized_items: list[dict] = []
    for item in items:
        if not isinstance(item, dict):
            continue
        link = (item.get("link") or item.get("originallink") or "").strip()
        normalized_items.append(
            {
                "title": _strip_html(item.get("title") or ""),
                "link": link,
                "description": _strip_html(item.get("description") or ""),
                "pubDate": item.get("pubDate") or "",
            }
        )
    return normalized_items


def _get_naver_credentials() -> tuple[str, str]:
    client_id = os.getenv("NAVER_CLIENT_ID") or getattr(settings, "NAVER_CLIENT_ID", "")
    client_secret = os.getenv("NAVER_CLIENT_SECRET") or getattr(
        settings, "NAVER_CLIENT_SECRET", ""
    )
    if not client_id or not client_secret:
        raise RuntimeError("NAVER_CLIENT_ID 또는 NAVER_CLIENT_SECRET이 설정되지 않았습니다")
    return client_id, client_secret


_HTML_TAG_PATTERN = re.compile(r"<[^>]+>")


def _strip_html(text: str) -> str:
    clean = _HTML_TAG_PATTERN.sub(" ", text)
    clean = unescape(clean)
    clean = re.sub(r"\s+", " ", clean)
    return clean.strip()
