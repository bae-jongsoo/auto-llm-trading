# 01. 공통 LLM 호출 및 응답 파싱

## 개요
뉴스 요약과 트레이딩 판단에서 공통으로 사용하는 LLM 호출/응답 파싱 로직을 구현한다.
비정상 응답은 기본 HOLD로 안전 처리할 수 있도록 표준 파서 함수를 제공한다.

## 테스트 대상 함수
- `shared/external/llm.py::ask_llm(prompt: str, timeout_seconds: int = 25) -> str`
- `shared/utils/json_helpers.py::parse_llm_json_object(raw_text: str) -> dict`
- `shared/utils/json_helpers.py::normalize_trade_decision(payload: dict) -> dict`

## 진입점(있는 경우)
- 없음

## 비즈니스 규칙
1. `ask_llm`은 `NANOBOT_BIN`(기본값 `nanobot`)으로 `nanobot agent --no-markdown -m <prompt>`를 실행한다.
2. `ask_llm`은 표준출력 문자열을 그대로 반환한다.
3. `parse_llm_json_object`는 JSON object만 허용하며, 파싱 불가 시 `ValueError`를 발생시킨다.
4. `normalize_trade_decision`은 `payload["decision"]`를 기준으로 결과를 정규화한다.
5. 허용 결과값은 `BUY`, `SELL`, `HOLD`만 인정하고, 그 외 값은 `HOLD`로 강등한다.
6. 수량/가격은 숫자형으로 정규화하며 0 이하 또는 누락 시 주문 불가 상태로 본다.
7. 파싱 실패/빈 응답/타임아웃은 호출 측(`apps/trader/services.py`)에서 기본 HOLD 처리로 분기할 수 있어야 한다.

## 에러 케이스
- `ask_llm` 타임아웃
- `ask_llm` 실행 실패(바이너리 없음, 비정상 종료)
- 빈 문자열/공백만 있는 응답
- JSON 파싱 실패
- JSON은 파싱되지만 `decision` 키가 없는 경우
- `result`가 허용값이 아닌 경우

## 참고
- 외부 연동: `nanobot` CLI
- 환경변수: `NANOBOT_BIN`
- 연계 모델: `apps/trader/models.py::DecisionHistory.result`
