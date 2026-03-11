## Iteration 1 - 2026-03-12 00:22
- 문제: 뉴스 요약 프롬프트 문자열 포맷팅 중 JSON 예시 중괄호가 포맷 변수로 해석되어 `KeyError`가 발생했다.
- 원인: `str.format()` 템플릿에서 리터럴 JSON 중괄호를 이스케이프하지 않았다.
- 가드레일: `str.format()` 템플릿에 JSON 리터럴을 넣을 때는 반드시 `{{` `}}`로 중괄호를 이스케이프한다.
- 체크: `pytest -q tests/test_news.py`

## 수동 추가 - 환경변수 정책
- 문제: `shared/external/naver_news.py`에서 `os.getenv()`를 직접 호출해 settings.py 우회.
- 원인: 환경변수를 settings.py에 등록하지 않고 코드에서 직접 읽음.
- 가드레일: `os.getenv()`는 `config/settings.py`에서만 사용. 앱/shared 코드는 `from django.conf import settings`로 읽는다. 테스트는 `@override_settings()` 사용.
- 체크: `grep -r "os.getenv" --include="*.py" apps/ shared/` 결과가 0건이어야 한다.

## Iteration 1 - 2026-03-12 01:01
- 문제: `pytest`를 병렬로 동시에 실행해 테스트 DB(`test_alt`) 생성 충돌이 발생했다.
- 원인: 같은 DB 이름을 사용하는 Django 테스트 실행을 중첩 실행했다.
- 가드레일: Django 테스트는 동시에 1개만 실행하고, 전체 테스트는 단일 `pytest -q tests`로 검증한다.
- 체크: `pytest -q tests`

## Iteration 1 - 2026-03-12 02:19
- 문제: Redis 가격 흐름 조회에서 상한 시각을 현재시각으로 고정해, 테스트에서 `now` 주입으로 저장된 미래 시각 틱이 조회되지 않았다.
- 원인: `ZRANGEBYSCORE`의 max 값을 동적 저장 시각이 아니라 조회 시각으로 제한했다.
- 가드레일: 저장 시각을 주입받는 시계열 조회는 상한을 `+inf` 또는 명시 전달값으로 두고 현재시각 고정을 피한다.
- 체크: `pytest -q tests/test_ws.py`
