## Iteration 1 - 2026-03-11 23:27
- 문제: `ask_llm`가 호출 시점 환경변수(`NANOBOT_BIN`)를 반영하지 않아 테스트 기대와 불일치했다.
- 원인: 설정값을 모듈/설정 객체에서 고정 참조해 런타임 환경 변경(patch.dict)을 읽지 못했다.
- 가드레일: 외부 실행 바이너리/토큰처럼 런타임에 바뀔 수 있는 값은 함수 내부에서 직접 환경변수를 조회한다.
- 체크: `PYTHONPATH="/tmp:$PYTHONPATH" pytest tests/test_llm_json_helpers.py -q --ds=alt_sqlite_settings`
