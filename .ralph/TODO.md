# 다음 할 일

## 현재 상태

이 프로젝트는 `init-ralph.sh`를 통해 **2단계 랄프 루프(방식 A)** 기반으로 자동 생성되었습니다.
Django Ninja 기반의 뼈대가 세팅되어 있고, 참고용 TODO 앱이 완성된 상태로 포함되어 있습니다.

### 자동으로 완료된 것

- [x] 프로젝트 폴더 + git 초기화
- [x] uv + pyproject.toml 기반 패키지 관리
- [x] Django 프로젝트 생성 (config/)
- [x] PostgreSQL 연결 설정 (.env + python-dotenv)
- [x] Redis 캐시 설정 (django-redis)
- [x] pytest + pytest-django 설정 (settings_test.py — Redis DB 15번)
- [x] TODO 예시 앱 완성 (apps/todos/)
  - 모델 (models.py) — Status 상태 전이 포함
  - 핸들러 (handlers.py) — 진입점 래퍼, 서비스 호출
  - API (api.py) + 스키마 (schemas.py) — Django Ninja Router
  - 통합 테스트 (tests/test_todos.py) — 완료 조건 패턴 예시
  - 단위 테스트 (apps/todos/tests/test_handlers.py)
  - Management command (apps/todos/management/commands/todo_list.py) — CLI 진입점 예시
- [x] PROJECT_RULES.md 초안 (AI가 아이디어 파일 기반으로 생성)
- [x] 아이디어 원문 보존 (.ralph/PRD.md)
- [x] 랄프 루프 스크립트 (ralph-loop.sh)
- [x] 프롬프트 파일 (.ralph/prompt-test-gen.md, .ralph/prompt-implement.md)
- [x] DB 마이그레이션 완료

---

## 다음 단계 (사람이 할 일)

### 1. PROJECT_RULES.md 리뷰 및 수정

AI가 아이디어 파일을 기반으로 초안을 생성했습니다.
열어서 확인하고, 프로젝트에 맞게 다듬으세요.
원문은 `.ralph/PRD.md`에 보존되어 있으니, 빠진 내용이 있으면 원문을 참고하세요.

특히 확인할 것:
- 프로젝트 개요가 의도와 맞는지
- 기술 스택이 정확한지
- DB 스키마, 환경변수 등 세부 내용이 빠지지 않았는지 (원문 대조)
- 테스트 전략이 올바른지 (통합 테스트 = 완료 조건, 단위 테스트 ≠ 완료 조건)
- 코딩 규칙 / 금지 사항에 빠진 것은 없는지

### 2. 모델 작성

apps/ 아래에 필요한 Django 앱을 만들고 모델을 정의하세요.
(랄프 루프에서 테스트를 먼저 만들려면 모델이 존재해야 합니다.)

```bash
uv run python manage.py startapp <앱이름> apps/<앱이름>
# apps.py의 name을 "apps.<앱이름>"으로 수정
# config/settings.py의 INSTALLED_APPS에 추가
# 모델 작성 후:
uv run python manage.py makemigrations
uv run python manage.py migrate
```

### 3. 태스크 스펙 작성

tasks/ 폴더에 태스크별 .md 파일을 작성하세요.
기존 예시(tests/test_todos.py)를 참고하면 어떤 수준으로 스펙을 적어야 하는지 감이 옵니다.

각 태스크에 포함할 것:
- API 스펙 (엔드포인트, 요청/응답, 에러 케이스)
- 비즈니스 규칙

### 4. 랄프 루프 실행

태스크마다 아래 순서를 반복합니다:

```bash
# 1차 루프: 통합 테스트 생성
./ralph-loop.sh .ralph/prompt-test-gen.md tasks/01-xxx.md 10

# 사람: 생성된 테스트 리뷰 + 수정
cat tests/test_xxx.py
git add -A && git commit -m "테스트 리뷰 완료: 01-xxx"

# 2차 루프: 구현 (테스트 통과시키기)
./ralph-loop.sh .ralph/prompt-implement.md tasks/01-xxx.md 20

# 검수
uv run pytest -v
```

### 참고: 코드 스타일 예시

새 앱을 만들 때 apps/todos/를 참고하세요:
- `models.py` — TextChoices, db_index, created_at/updated_at
- `handlers.py` — 진입점 래퍼, 서비스 호출, 커스텀 예외 정의
- `services.py` — 비즈니스 로직 (복잡해지면 여기로 분리)
- `api.py` — Django Ninja Router, 스키마 기반 입출력, 서비스만 호출
- `management/commands/todo_list.py` — 서비스 레이어 호출, add_arguments 패턴
- `tests/test_todos.py` — 서비스를 직접 호출하여 검증 (stdout/응답에 의존 금지), 정상 흐름은 mock 금지, 에러 시뮬레이션은 fixture + unittest.mock.patch
