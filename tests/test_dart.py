from datetime import datetime
from unittest.mock import patch

import pytest
from django.test import override_settings
from django.utils import timezone

from apps.dart.models import DartDisclosure
from apps.dart.services import collect_dart, upsert_disclosures
from shared.external.dart_api import fetch_disclosures
from shared.stock_universe import resolve_target_corp_codes

EXPECTED_TARGET_CORP_CODES = {
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


def _공시_행(
    *,
    rcept_no: str,
    title: str = "주요사항보고서",
    link: str = "https://dart.fss.or.kr/dsaf001/main.do?rcpNo=20260311000001",
    description: str | None = "공시 본문 요약",
    published_at: datetime | None = None,
) -> dict:
    return {
        "rcept_no": rcept_no,
        "title": title,
        "report_nm": title,
        "link": link,
        "description": description,
        "published_at": published_at,
    }


def _호출_인자에서_법인코드_목록(call_args_list: list) -> list[str]:
    corp_codes: list[str] = []
    for one_call in call_args_list:
        if one_call.args:
            corp_codes.append(one_call.args[0])
            continue
        if "corp_code" in one_call.kwargs:
            corp_codes.append(one_call.kwargs["corp_code"])
            continue
        corp_codes.append(one_call.kwargs["corp"])
    return corp_codes


# ──────────────────────────────────────
# resolve_target_corp_codes
# ──────────────────────────────────────

def test_대상_법인코드_기본조회_성공_10종목():
    result = resolve_target_corp_codes()

    assert isinstance(result, dict)
    assert len(result) == 10
    assert result == EXPECTED_TARGET_CORP_CODES


def test_대상_법인코드_입력한_종목만_조회_중복제거():
    result = resolve_target_corp_codes(["005930", "000660", "005930"])

    assert result == {
        "005930": "00126380",
        "000660": "00164779",
    }


def test_대상_법인코드_지원하지_않는_종목코드_실패():
    with pytest.raises(RuntimeError, match="corp_code|매핑|누락"):
        resolve_target_corp_codes(["999999"])


def test_대상_법인코드_매핑누락_실패():
    with patch.dict(
        "shared.stock_universe.__dict__",
        {"TARGET_CORP_CODES": {"005930": "00126380"}},
    ):
        with pytest.raises(RuntimeError, match="corp_code|매핑|누락"):
            resolve_target_corp_codes(["000660"])


# ──────────────────────────────────────
# fetch_disclosures
# ──────────────────────────────────────

@override_settings(DART_API_KEY="dart-test-key")
def test_다트_API_공시조회_성공():
    expected_rows = [
        {
            "rcept_no": "20260311000001",
            "title": "사업보고서",
            "description": "사업보고서 요약",
            "published_at": "2026-03-11T09:00:00+09:00",
        }
    ]

    with patch("shared.external.dart_api.OpenDartReader") as mock_reader_cls:
        mock_reader = mock_reader_cls.return_value
        mock_reader.list.return_value = expected_rows

        rows = fetch_disclosures("00126380")

    assert rows == expected_rows
    mock_reader_cls.assert_called_once_with("dart-test-key")
    mock_reader.list.assert_called_once()


@override_settings(DART_API_KEY="")
def test_다트_API키_누락_실패():
    with pytest.raises(RuntimeError, match="DART_API_KEY|설정"):
        fetch_disclosures("00126380")


@override_settings(DART_API_KEY="dart-test-key")
def test_다트_API_호출실패():
    with patch("shared.external.dart_api.OpenDartReader") as mock_reader_cls:
        mock_reader = mock_reader_cls.return_value
        mock_reader.list.side_effect = RuntimeError("OpenDartReader 오류")

        with pytest.raises(RuntimeError, match="OpenDartReader|호출|실패"):
            fetch_disclosures("00126380")


# ──────────────────────────────────────
# upsert_disclosures
# ──────────────────────────────────────

@pytest.mark.django_db
def test_공시_upsert_성공_외부키기반_멱등저장():
    published_at = timezone.now().replace(microsecond=0)

    created = upsert_disclosures(
        "005930",
        "00126380",
        [_공시_행(rcept_no="20260311000010", title="최초 공시", published_at=published_at)],
    )
    updated = upsert_disclosures(
        "005930",
        "00126380",
        [_공시_행(rcept_no="20260311000010", title="수정 공시", published_at=published_at)],
    )

    assert len(created) == 1
    assert len(updated) == 1
    assert DartDisclosure.objects.count() == 1

    saved = DartDisclosure.objects.get()
    assert saved.stock_code == "005930"
    assert saved.corp_code == "00126380"
    assert saved.rcept_no == "20260311000010"
    assert saved.title == "수정 공시"
    assert saved.external_id == DartDisclosure.build_external_id("00126380", "20260311000010")
    assert saved.published_at == published_at


@pytest.mark.django_db
def test_공시_upsert_description_없으면_None_허용():
    saved = upsert_disclosures(
        "005930",
        "00126380",
        [_공시_행(rcept_no="20260311000011", description=None, published_at=None)],
    )[0]

    assert saved.description is None
    assert saved.published_at is None


@pytest.mark.django_db
def test_공시_upsert_rcept_no_누락시_실패():
    with pytest.raises(ValueError, match="rcept_no|external_id|필수"):
        upsert_disclosures(
            "005930",
            "00126380",
            [{"title": "접수번호 누락"}],
        )


# ──────────────────────────────────────
# collect_dart
# ──────────────────────────────────────

@pytest.mark.django_db
@override_settings(DART_API_KEY="dart-test-key")
def test_다트_수집_성공_법인코드기준_호출_및_DB저장():
    with patch("shared.external.dart_api.OpenDartReader") as mock_reader_cls:
        mock_reader = mock_reader_cls.return_value
        mock_reader.list.side_effect = [
            [_공시_행(rcept_no="20260311000101", title="삼성 공시")],
            [_공시_행(rcept_no="20260311000102", title="하이닉스 공시")],
        ]

        result = collect_dart(stock_codes=["005930", "000660"])

    assert isinstance(result, dict)
    assert DartDisclosure.objects.count() == 2
    assert _호출_인자에서_법인코드_목록(mock_reader.list.call_args_list) == [
        "00126380",
        "00164779",
    ]


@pytest.mark.django_db
@override_settings(DART_API_KEY="dart-test-key")
def test_다트_수집_stock_codes_미지정시_대상10종목_전체호출():
    with patch("shared.external.dart_api.OpenDartReader") as mock_reader_cls:
        mock_reader = mock_reader_cls.return_value
        mock_reader.list.return_value = []

        result = collect_dart()

    assert isinstance(result, dict)
    assert mock_reader.list.call_count == 10
    assert set(_호출_인자에서_법인코드_목록(mock_reader.list.call_args_list)) == set(
        EXPECTED_TARGET_CORP_CODES.values()
    )




@pytest.mark.django_db
@override_settings(DART_API_KEY="dart-test-key")
def test_다트_수집_외부호출_실패():
    with patch("shared.external.dart_api.OpenDartReader") as mock_reader_cls:
        mock_reader = mock_reader_cls.return_value
        mock_reader.list.side_effect = RuntimeError("OpenDartReader 실패")

        with pytest.raises(RuntimeError, match="OpenDartReader|호출|실패"):
            collect_dart(stock_codes=["005930"])
