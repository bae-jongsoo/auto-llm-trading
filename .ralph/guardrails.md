## Iteration 1 - 2026-03-12 00:22
- 문제: 뉴스 요약 프롬프트 문자열 포맷팅 중 JSON 예시 중괄호가 포맷 변수로 해석되어 `KeyError`가 발생했다.
- 원인: `str.format()` 템플릿에서 리터럴 JSON 중괄호를 이스케이프하지 않았다.
- 가드레일: `str.format()` 템플릿에 JSON 리터럴을 넣을 때는 반드시 `{{` `}}`로 중괄호를 이스케이프한다.
- 체크: `pytest -q tests/test_news.py`
