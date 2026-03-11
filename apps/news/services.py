from __future__ import annotations

from email.utils import parsedate_to_datetime

from django.db import transaction
from django.utils import timezone

from apps.news.models import News
from shared.external.llm import ask_llm
from shared.external.naver_news import fetch_news
from shared.external.web_content import extract_article_text
from shared.stock_universe import resolve_stock_codes, validate_stock_code
from shared.utils.json_helpers import parse_llm_json_object

NEWS_SUMMARY_PROMPT_TEMPLATE = """아래는 뉴스 본문이다. 이걸 요약하고 주식 단타에 도움이 되는지 판단 후,
{{"summary": "...", "useful": true}} 형태로 응답 해달라.

<뉴스 본문>
{article_text}
"""


def upsert_news_items(stock_code: str, items: list[dict]) -> list[News]:
    normalized_stock_code = validate_stock_code(stock_code)

    saved_news: list[News] = []
    with transaction.atomic():
        for item in items:
            link = (item.get("link") or "").strip()
            if not link:
                raise ValueError("link 필수값이 누락되었습니다")

            external_id = News.build_external_id(normalized_stock_code, link)
            news, _ = News.objects.update_or_create(
                external_id=external_id,
                defaults={
                    "stock_code": normalized_stock_code,
                    "link": link,
                    "title": (item.get("title") or "").strip(),
                    "description": (item.get("description") or "").strip() or None,
                    "published_at": _parse_published_at(item.get("pubDate")),
                },
            )
            saved_news.append(news)

    return saved_news


def summarize_news(news: News) -> News:
    try:
        article_text = extract_article_text(news.link)
    except Exception:
        news.summary = news.description
        news.useful = None
        news.save(update_fields=["summary", "useful"])
        return news

    prompt = NEWS_SUMMARY_PROMPT_TEMPLATE.format(article_text=article_text)
    raw_response = ask_llm(prompt)
    parsed = parse_llm_json_object(raw_response)

    summary = (parsed.get("summary") or "").strip()
    if not summary:
        raise ValueError("LLM 요약 결과에 summary가 없습니다")

    useful = parsed.get("useful")
    if useful is None:
        raise ValueError("LLM 요약 결과에 useful이 없습니다")
    if isinstance(useful, str):
        useful = useful.strip().lower() == "true"
    else:
        useful = bool(useful)

    news.summary = summary
    news.useful = useful
    news.save(update_fields=["summary", "useful"])
    return news


def collect_news(stock_codes: list[str] | None = None, limit: int = 10) -> dict:
    if limit <= 0:
        raise ValueError("limit은 1 이상이어야 합니다")

    target_stock_codes = resolve_stock_codes(stock_codes)

    fetched_items_count = 0
    saved_items_count = 0
    summarized_items_count = 0

    for stock_code in target_stock_codes:
        normalized_stock_code = validate_stock_code(stock_code)
        fetched_items = fetch_news(normalized_stock_code, limit)
        fetched_items_count += len(fetched_items)

        saved_items = upsert_news_items(normalized_stock_code, fetched_items)
        saved_items_count += len(saved_items)

        for news in saved_items:
            summarize_news(news)
            summarized_items_count += 1

    return {
        "stock_codes": target_stock_codes,
        "fetched_items": fetched_items_count,
        "saved_items": saved_items_count,
        "summarized_items": summarized_items_count,
    }


def _parse_published_at(raw_pub_date: str | None):
    if raw_pub_date:
        try:
            published_at = parsedate_to_datetime(raw_pub_date)
            if timezone.is_naive(published_at):
                return timezone.make_aware(
                    published_at,
                    timezone=timezone.get_current_timezone(),
                )
            return published_at.astimezone(timezone.get_current_timezone())
        except (TypeError, ValueError, IndexError):
            pass
    return timezone.now()
