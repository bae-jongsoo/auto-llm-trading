from unittest.mock import call, patch

import pytest
from django.utils import timezone

from apps.news.models import News
from apps.news.services import collect_news, summarize_news, upsert_news_items
from shared.stock_universe import TARGET_STOCKS


def _네이버_아이템(
    *,
    link: str,
    title: str = "뉴스 제목",
    description: str = "요약 설명",
    pub_date: str = "Wed, 11 Mar 2026 09:00:00 +0900",
) -> dict:
    return {
        "title": title,
        "link": link,
        "description": description,
        "pubDate": pub_date,
    }


def _뉴스_생성(
    *,
    stock_code: str = "005930",
    link: str = "https://news.example.com/article/1",
    title: str = "초기 제목",
    description: str = "초기 설명",
) -> News:
    return News.objects.create(
        stock_code=stock_code,
        external_id=News.build_external_id(stock_code, link),
        link=link,
        title=title,
        description=description,
    )


# ──────────────────────────────────────
# upsert_news_items
# ──────────────────────────────────────

@pytest.mark.django_db
def test_뉴스_upsert_성공_외부키_중복방지_시간대저장():
    item = _네이버_아이템(link="https://news.example.com/article/100", title="최초 제목")
    updated_item = _네이버_아이템(
        link="https://news.example.com/article/100",
        title="변경 제목",
        description="변경 설명",
    )

    with patch("apps.news.services.News.build_external_id", wraps=News.build_external_id) as mock_build:
        created = upsert_news_items("005930", [item])
        updated = upsert_news_items("005930", [updated_item])

    assert len(created) == 1
    assert len(updated) == 1
    assert mock_build.call_count >= 2
    assert News.objects.count() == 1

    saved = News.objects.get()
    assert saved.title == "변경 제목"
    assert saved.description == "변경 설명"
    assert saved.external_id == News.build_external_id("005930", "https://news.example.com/article/100")
    assert timezone.is_aware(saved.published_at)
    assert timezone.is_aware(saved.created_at)
    assert timezone.localtime(saved.published_at).utcoffset().total_seconds() == 9 * 60 * 60


@pytest.mark.django_db
def test_뉴스_upsert_API아이템_link_누락_실패():
    with pytest.raises(ValueError, match="link|필수"):
        upsert_news_items(
            "005930",
            [
                {
                    "title": "링크 없음",
                    "description": "요약",
                    "pubDate": "Wed, 11 Mar 2026 09:00:00 +0900",
                }
            ],
        )


# ──────────────────────────────────────
# summarize_news
# ──────────────────────────────────────

@pytest.mark.django_db
def test_뉴스_요약_성공_본문크롤링후_LLM결과_반영():
    news = _뉴스_생성()

    with patch("apps.news.services.extract_article_text", return_value="기사 본문 텍스트") as mock_extract:
        with patch(
            "apps.news.services.ask_llm",
            return_value='{"summary": "핵심 요약", "useful": true}',
        ) as mock_llm:
            updated = summarize_news(news)

    assert updated.id == news.id
    assert updated.summary == "핵심 요약"
    assert updated.useful is True
    mock_extract.assert_called_once_with(news.link)
    mock_llm.assert_called_once()


@pytest.mark.django_db
def test_뉴스_요약_본문크롤링_실패시_description_fallback():
    news = _뉴스_생성(description="네이버 제공 설명")

    with patch("apps.news.services.extract_article_text", side_effect=RuntimeError("crawl fail")):
        with patch("apps.news.services.ask_llm") as mock_llm:
            updated = summarize_news(news)

    assert updated.summary == "네이버 제공 설명"
    assert updated.useful is None
    mock_llm.assert_not_called()


@pytest.mark.django_db
def test_뉴스_요약_LLM_타임아웃_실패():
    news = _뉴스_생성()

    with patch("apps.news.services.extract_article_text", return_value="기사 본문 텍스트"):
        with patch("apps.news.services.ask_llm", side_effect=TimeoutError("timeout")):
            with pytest.raises(TimeoutError, match="timeout|Timeout"):
                summarize_news(news)


@pytest.mark.django_db
def test_뉴스_요약_LLM_파싱실패_실패():
    news = _뉴스_생성()

    with patch("apps.news.services.extract_article_text", return_value="기사 본문 텍스트"):
        with patch("apps.news.services.ask_llm", return_value="not-json"):
            with pytest.raises(ValueError, match="JSON|파싱"):
                summarize_news(news)


@pytest.mark.django_db
def test_뉴스_요약_LLM_빈응답_실패():
    news = _뉴스_생성()

    with patch("apps.news.services.extract_article_text", return_value="기사 본문 텍스트"):
        with patch("apps.news.services.ask_llm", return_value="   "):
            with pytest.raises(ValueError, match="빈|empty|응답"):
                summarize_news(news)


# ──────────────────────────────────────
# collect_news
# ──────────────────────────────────────

@pytest.mark.django_db
def test_뉴스_수집_성공_종목별_저장_및_요약():
    code_1 = "005930"
    code_2 = "000660"

    with patch("apps.news.services.fetch_news") as mock_fetch:
        with patch("apps.news.services.extract_article_text", return_value="기사 본문 텍스트"):
            with patch(
                "apps.news.services.ask_llm",
                return_value='{"summary": "요약됨", "useful": false}',
            ):
                mock_fetch.side_effect = [
                    [
                        _네이버_아이템(link="https://news.example.com/article/201"),
                        _네이버_아이템(link="https://news.example.com/article/202"),
                    ],
                    [_네이버_아이템(link="https://news.example.com/article/203")],
                ]
                result = collect_news(stock_codes=[code_1, code_2], limit=2)

    assert isinstance(result, dict)
    assert News.objects.count() == 3
    assert News.objects.filter(useful=False, summary="요약됨").count() == 3
    assert mock_fetch.call_args_list == [call(code_1, 2), call(code_2, 2)]


@pytest.mark.django_db
def test_뉴스_수집_stock_codes_미지정시_대상10종목_전체호출():
    with patch("apps.news.services.fetch_news", return_value=[]) as mock_fetch:
        result = collect_news(limit=1)

    assert isinstance(result, dict)
    assert mock_fetch.call_count == len(TARGET_STOCKS)
    assert {c.args[0] for c in mock_fetch.call_args_list} == set(TARGET_STOCKS.keys())
    assert all(c.args[1] == 1 for c in mock_fetch.call_args_list)


@pytest.mark.django_db
def test_뉴스_수집_네이버_API_호출실패():
    with patch("apps.news.services.fetch_news", side_effect=RuntimeError("네이버 API 오류")):
        with pytest.raises(RuntimeError, match="네이버|API|오류|실패"):
            collect_news(stock_codes=["005930"], limit=1)


