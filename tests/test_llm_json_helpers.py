import os
import subprocess
from unittest.mock import MagicMock, patch

import pytest
from shared.external.llm import ask_llm
from shared.utils.json_helpers import normalize_trade_decision, parse_llm_json_object


# ──────────────────────────────────────
# Fixtures
# ──────────────────────────────────────

@pytest.fixture
def mock_subprocess_run():
    """LLM CLI subprocess 호출을 mock한다. 외부 경계 mock의 표준 패턴."""
    with patch("shared.external.llm.subprocess.run") as mock_run:
        yield mock_run


# ──────────────────────────────────────
# ask_llm
# ──────────────────────────────────────

def test_ask_llm_기본_바이너리_호출_및_stdout_반환(mock_subprocess_run):
    mock_subprocess_run.return_value = MagicMock(
        returncode=0,
        stdout='{"decision":{"result":"HOLD"}}',
        stderr="",
    )

    with patch.dict(os.environ, {}, clear=True):
        raw = ask_llm("테스트 프롬프트", timeout_seconds=7)

    assert raw == '{"decision":{"result":"HOLD"}}'
    mock_subprocess_run.assert_called_once_with(
        ["nanobot", "agent", "--no-markdown", "-m", "테스트 프롬프트"],
        capture_output=True,
        text=True,
        timeout=7,
        check=False,
    )


def test_ask_llm_NANOBOT_BIN_환경변수_사용(mock_subprocess_run):
    mock_subprocess_run.return_value = MagicMock(returncode=0, stdout="ok", stderr="")

    with patch.dict(os.environ, {"NANOBOT_BIN": "/usr/local/bin/custom-bot"}, clear=True):
        ask_llm("프롬프트")

    called_args = mock_subprocess_run.call_args[0][0]
    assert called_args[0] == "/usr/local/bin/custom-bot"


def test_ask_llm_타임아웃_실패():
    with patch(
        "shared.external.llm.subprocess.run",
        side_effect=subprocess.TimeoutExpired(cmd="nanobot", timeout=25),
    ):
        with pytest.raises(subprocess.TimeoutExpired):
            ask_llm("타임아웃 테스트")


def test_ask_llm_바이너리_없음_실패():
    with patch("shared.external.llm.subprocess.run", side_effect=FileNotFoundError("nanobot")):
        with pytest.raises(FileNotFoundError, match="nanobot"):
            ask_llm("실행 실패 테스트")


def test_ask_llm_비정상_종료_실패(mock_subprocess_run):
    mock_subprocess_run.return_value = MagicMock(returncode=1, stdout="", stderr="fatal error")

    with pytest.raises(RuntimeError, match="비정상|종료|실패"):
        ask_llm("비정상 종료 테스트")


# ──────────────────────────────────────
# parse_llm_json_object
# ──────────────────────────────────────

def test_parse_llm_json_object_성공():
    payload = parse_llm_json_object('{"decision":{"result":"BUY","quantity":1,"price":70000}}')

    assert payload["decision"]["result"] == "BUY"
    assert payload["decision"]["quantity"] == 1
    assert payload["decision"]["price"] == 70000


def test_parse_llm_json_object_빈_응답_실패():
    with pytest.raises(ValueError, match="빈|empty|응답"):
        parse_llm_json_object("   ")


def test_parse_llm_json_object_파싱_실패():
    with pytest.raises(ValueError, match="JSON|파싱|decode"):
        parse_llm_json_object("not-json")


def test_parse_llm_json_object_object_외_타입_실패():
    with pytest.raises(ValueError, match="object|객체|dict"):
        parse_llm_json_object('["BUY", "SELL"]')


# ──────────────────────────────────────
# normalize_trade_decision
# ──────────────────────────────────────

def test_normalize_trade_decision_성공_BUY_정규화():
    normalized = normalize_trade_decision(
        {
            "decision": {
                "result": "BUY",
                "stock_code": "005930",
                "quantity": "3",
                "price": "71200",
            }
        }
    )

    decision = normalized["decision"]
    assert decision["result"] == "BUY"
    assert decision["stock_code"] == "005930"
    assert isinstance(decision["quantity"], (int, float))
    assert isinstance(decision["price"], (int, float))
    assert decision["quantity"] == 3
    assert decision["price"] == 71200


def test_normalize_trade_decision_decision_키_없음_실패():
    with pytest.raises(ValueError, match="decision"):
        normalize_trade_decision({"result": "BUY"})


def test_normalize_trade_decision_허용되지_않은_result는_HOLD_강등():
    normalized = normalize_trade_decision(
        {"decision": {"result": "STRONG_BUY", "stock_code": "005930", "quantity": 5, "price": 70000}}
    )

    assert normalized["decision"]["result"] == "HOLD"


def test_normalize_trade_decision_수량_가격_누락_또는_0이하이면_주문불가_HOLD():
    normalized = normalize_trade_decision(
        {"decision": {"result": "BUY", "stock_code": "005930", "quantity": 0, "price": None}}
    )

    assert normalized["decision"]["result"] == "HOLD"
